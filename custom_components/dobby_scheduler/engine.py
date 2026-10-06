"""Pure scheduling logic. No Home Assistant imports, I/O, or device commands.

All device side effects are returned explicitly. The adapter must persist state
BEFORE executing them. A docked state alone is never completion evidence.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from datetime import datetime, timedelta
import math
import uuid

MODES = {"vacuum", "vac_and_mop", "mop"}
DEFAULTS = {
    "vacuum_entity": "", "presence_entity": "", "mode_entity": "",
    "battery_entity": "", "error_entity": "", "map_entity": "",
    "empty_entity": "", "wash_entity": "", "water_problem_entities": [],
    "blocking_entities": [], "completion_entity": "",
    "away_minutes": 15, "minimum_battery": 40, "reset_time": "00:05",
    "window_start": "08:00", "window_end": "21:00",
    "gesture_seconds": 2.0, "gesture_cooldown": 5.0,
    "reject_automation_context": True, "acknowledge": True,
    "empty_after_room": True, "empty_after_mop": True,
    "start_timeout": 300, "room_timeout": 7200, "dock_timeout": 600,
    "proof_timeout": 240, "empty_timeout": 240, "dock_settle": 10,
    "mop_intensity_entity": "", "mop_intensity": "medium",
    # Optional read-only reporting sources; blank = conventional-name discovery.
    "current_room_entity": "", "status_entity": "", "dock_error_entity": "",
    "drying_entity": "", "room_confirm_seconds": 60,
}


def number(value):
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (ValueError, TypeError):
        return None


def clock_minutes(value):
    h, m = str(value).split(":")
    h, m = int(h), int(m)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError("Use a 24-hour HH:MM time")
    return h * 60 + m


def in_window(local_now, start, end):
    a, b = clock_minutes(start), clock_minutes(end)
    n = local_now.hour * 60 + local_now.minute
    return True if a == b else (a <= n < b if a < b else n >= a or n < b)


def cleaning_day(local_now, reset_time):
    """Reset once per local cleaning day, including DST and missed midnight."""
    cut = clock_minutes(reset_time)
    d = local_now.date()
    if local_now.hour * 60 + local_now.minute < cut:
        d -= timedelta(days=1)
    return d.isoformat()


def resolve_mode(labels):
    choices = []
    if "dobby_vacuum" in labels:
        choices.append("vacuum")
    if "dobby_vacuum_mop" in labels:
        choices.append("vac_and_mop")
    if "dobby_mop" in labels:
        choices.append("mop")
    if len(choices) > 1:
        return None, "Conflicting Dobby mode labels"
    if not choices:
        return "vacuum", "No mode label: using vacuum only"
    return choices[0], ""


def validate_segments(values):
    if isinstance(values, str):
        values = values.replace(";", ",").split(",")
    if not isinstance(values, list) or not values:
        raise ValueError("Select at least one room number")
    out = []
    for value in values:
        if isinstance(value, bool) or str(value).strip() == "":
            raise ValueError("Room numbers must be positive integers")
        n = number(value)
        if n is None or n != int(n) or not 1 <= n <= 65535:
            raise ValueError("Room numbers must be integers from 1 to 65535")
        out.append(int(n))
    return sorted(set(out))


class GestureDetector:
    """Two or four real on/off transitions in one window; never count attributes.

State strings must alternate. Unknown/unavailable resets the sequence. Each
entity has its own window, so toggles on two switches cannot combine.
"""
    def __init__(self):
        self.windows = {}
        self.cooldowns = {}

    def feed(self, entity, old, new, now, window=2.0, cooldown=5.0,
             automation=False, reject_automation=True, transitions=4):
        if transitions not in (2, 4):
            raise ValueError("Switch gesture must have two or four transitions")
        if old not in ("on", "off") or new not in ("on", "off"):
            self.windows.pop(entity, None)
            return False
        if old == new:
            return False
        if automation and reject_automation:
            self.windows.pop(entity, None)
            return False
        if now < self.cooldowns.get(entity, 0):
            return False
        q = self.windows.setdefault(entity, deque(maxlen=transitions))
        if q.maxlen != transitions:
            q = self.windows[entity] = deque(maxlen=transitions)
        if q and q[-1][1] != old:
            q.clear()
        if q and now - q[-1][0] < 0.06:  # Contact bounce/duplicate mirror events.
            return False
        q.append((now, new))
        while q and now - q[0][0] > window:
            q.popleft()
        if len(q) != transitions:
            return False
        self.windows.pop(entity, None)
        self.cooldowns[entity] = now + cooldown
        return True


class Engine:
    """Persistent ordered jobs and an explicit, conservative execution state."""
    def __init__(self, saved=None):
        d = deepcopy(saved or {})
        self.jobs = d.get("jobs", [])
        self.active = d.get("active")
        self.enabled = bool(d.get("enabled", False))
        self.day = d.get("day", "")
        self.fault = d.get("fault", "")
        self.log = d.get("log", [])[-60:]
        self.manual = False  # Never restore permission to run in an occupied house.
        self.allow_home = False
        self.away_since = None
        self.reset_deferred = False
        self.wait_reason = "Disabled"
        self.last_effects = []
        if self.active:
            self.active.update(phase="aborting", interrupted=True,
                               reason="Home Assistant restarted; room remains pending",
                               dock_issued=0, dock_attempts=0)

    def export(self):
        return deepcopy({"jobs": self.jobs, "active": self.active,
                         "enabled": self.enabled, "day": self.day,
                         "fault": self.fault, "log": self.log[-60:]})

    def note(self, text, now):
        self.log.append({"at": now, "message": str(text)[:500]})
        self.log = self.log[-60:]

    def find(self, uid):
        return next((j for j in self.jobs if j["uid"] == uid), None)

    def enqueue(self, area, rooms, now, urgent=False, source="dashboard"):
        r = rooms.get(area)
        if not r or not r.get("cleanable"):
            raise ValueError("Choose an Area labelled dobby_cleanable")
        j = next((j for j in self.jobs if j["area_id"] == area), None)
        if j is None:
            j = {"uid": uuid.uuid4().hex, "area_id": area, "status": "needs_action",
                 "source": source, "requested_at": now, "completed_at": None,
                 "note": "", "reason": "", "urgent": urgent}
            self.jobs.append(j)
        elif not self.active or self.active["uid"] != j["uid"]:
            j.update(status="needs_action", completed_at=None, source=source,
                     requested_at=now, reason="", urgent=urgent)
        if urgent and (not self.active or self.active["uid"] != j["uid"]):
            self.jobs.remove(j)
            self.jobs.insert(0, j)
        self.note(f"Queued {r['name']}" + (" as next room" if urgent else ""), now)
        return j["uid"]

    def move(self, uid, previous_uid=None):
        job = self.find(uid)
        if not job:
            raise ValueError("Queue item no longer exists")
        if previous_uid == uid:
            return
        if previous_uid is not None and not self.find(previous_uid):
            raise ValueError("Previous queue item no longer exists")
        self.jobs.remove(job)
        pos = 0 if previous_uid is None else next(i + 1 for i, j in enumerate(self.jobs) if j["uid"] == previous_uid)
        self.jobs.insert(pos, job)

    def remove(self, uid):
        if self.active and self.active["uid"] == uid:
            raise ValueError("Dock/pause Dobby before removing the current room")
        self.jobs = [j for j in self.jobs if j["uid"] != uid]

    def reset(self, day, rooms, now):
        if self.active:
            self.reset_deferred = True
            return False
        self.jobs = []
        self.day = day
        for r in sorted(rooms.values(), key=lambda r: (r.get("priority", 100), r["name"].casefold())):
            if r.get("daily") and r.get("cleanable"):
                self.enqueue(r["area_id"], rooms, now, source="daily")
        self.manual = self.allow_home = False
        self.reset_deferred = False
        self.note("Restored daily rooms and default order", now)
        return True

    def abort(self, reason, now, latch=False):
        if latch:
            self.fault = reason
        if self.active and self.active["phase"] != "aborting":
            self.active.update(phase="aborting", interrupted=True, reason=reason,
                               dock_issued=0, dock_attempts=0)
            self.note(reason, now)
        self.manual = self.allow_home = False

    def fault_effect(self, effect, error, now):
        self.fault = f"{effect}: {error}"
        self.note(self.fault, now)
        if self.active:
            self.active["reason"] = self.fault
            self.active["command_uncertain"] = True
        # A failed service is not automatically retried: the robot may have received it.

    def retry(self, now, docked):
        if not docked:
            raise ValueError("Dock Dobby before retrying")
        self.fault = ""
        a = self.active
        if a and a.get("proved") and not a.get("interrupted"):
            a.update(phase="verifying", docked_since=now, phase_at=now,
                     empty_seen=False, empty_finished=False, command_uncertain=False)
        elif a:
            j = self.find(a["uid"])
            if j:
                j["reason"] = "Retry requested"
            self.active = None
        self.note("Retry authorised", now)

    def manual_complete(self, uid, now, docked):
        if not docked:
            raise ValueError("Rooms can only be marked complete while Dobby is docked")
        j = self.find(uid)
        if not j:
            raise ValueError("Queue item no longer exists")
        if self.active and self.active["uid"] != uid:
            raise ValueError("Another job is still active")
        j.update(status="completed", completed_at=now, reason="Manually confirmed by a user")
        if self.active and self.active["uid"] == uid:
            self.active = None
            self.fault = ""
        self.note("User manually marked a room complete", now)

    @staticmethod
    def record_matches(a, record, now):
        if not record or not a.get("command_at"):
            return False
        begin, end = number(record.get("begin")), number(record.get("end"))
        if begin is None or end is None or end <= begin or end > now + 60:
            return False
        if (begin, end) == tuple(a.get("baseline_record", [])):
            return False
        if not (a["command_at"] - 15 <= begin <= a["command_at"] + a["start_timeout"]):
            return False
        if end < a["command_at"]:
            return False
        flag = record.get("map_flag")
        if flag is not None and str(flag) != str(a["map_flag"]):
            return False
        return True

    @staticmethod
    def record_success(record):
        return (record.get("complete") in (True, 1) and
                number(record.get("error")) == 0 and
                (number(record.get("area")) or 0) > 0)

    def _preflight(self, t, cfg, r):
        if not r or not r.get("cleanable"):
            return "Next room is not labelled dobby_cleanable"
        if not r.get("mode"):
            return "Next room has conflicting mode labels"
        if not r.get("verified") or not r.get("segments"):
            return "Verify the next room's map and segment numbers in Setup"
        if r.get("mapping_error"):
            return r["mapping_error"]
        if not t.get("connected"):
            return "Dobby is unavailable"
        if t.get("map_name") != r.get("map_name"):
            return "Selected Roborock map does not match the next room"
        if t.get("map_flag") is not None and str(t["map_flag"]) != str(r.get("map_flag")):
            return "Active map ID does not match the next room"
        if t.get("vacuum") != "docked":
            return "Waiting for Dobby to dock"
        if t.get("battery") is None or t["battery"] < cfg["minimum_battery"]:
            return "Waiting for sufficient battery"
        if t.get("error") != "ok":
            return "Vacuum error is present or unavailable"
        if t.get("blockers"):
            return "A configured pause/blocking entity is active or unavailable"
        if t.get("legacy"):
            return "Old Dobby scheduling automations are still enabled"
        if not t.get("record_supported"):
            return "No reliable completed-clean record is available; see Diagnostics"
        if r["mode"] not in t.get("mode_options", []):
            return "Cleaning-mode selector does not support the requested mode"
        if r["mode"] != "vacuum" and not t.get("wet_ok", False):
            return "Mop/water sensor unavailable or water system needs attention"
        if cfg["empty_after_room"] and (r["mode"] != "mop" or cfg["empty_after_mop"]):
            if t.get("emptying") is None:
                return "Dust-emptying switch unavailable or not configured"
        if t.get("emptying") or t.get("washing"):
            return "Waiting for dock service to finish"
        return ""

    def tick(self, t, cfg, rooms, local_now):
        now = t["now"]
        effects = []
        home = t.get("home")
        if home is False:
            if self.away_since is None:
                self.away_since = now
        else:
            self.away_since = None
        day = cleaning_day(local_now, cfg["reset_time"])
        if day != self.day:
            self.reset(day, rooms, now)
        if self.active:
            a = self.active
            if a["phase"] != "aborting":
                reason = ""
                if home is None:
                    reason = "Home presence unavailable; returning to dock"
                elif home and not self.allow_home:
                    reason = "Someone arrived home; room remains pending"
                elif not (self.enabled or self.manual):
                    reason = "Scheduler paused; room remains pending"
                elif not in_window(local_now, cfg["window_start"], cfg["window_end"]):
                    reason = "Cleaning window ended; room remains pending"
                elif t.get("blockers"):
                    reason = "A pause/blocking entity became active"
                elif t.get("map_name") != a["map_name"]:
                    reason = "Active map changed during the job"
                if reason:
                    self.abort(reason, now)
                    a = self.active
            if a["phase"] == "aborting":
                self.wait_reason = a["reason"]
                if t.get("vacuum") == "docked" and not t.get("emptying") and not t.get("washing"):
                    j = self.find(a["uid"])
                    if j:
                        j["reason"] = a["reason"]
                    self.active = None
                elif t.get("connected") and t.get("vacuum") != "docked" and now - a.get("dock_issued", 0) >= 30 and a.get("dock_attempts", 0) < 3:
                    a["dock_issued"] = now
                    a["dock_attempts"] = a.get("dock_attempts", 0) + 1
                    effects.append({"kind": "dock"})
                return effects
            if self.fault:
                self.wait_reason = self.fault
                return []
            if not t.get("connected"):
                a.setdefault("lost_since", now)
                self.wait_reason = "Waiting for connection; completion is not assumed"
                if now - a["lost_since"] > cfg["dock_timeout"]:
                    self.abort("Connection lost too long; room pending", now, latch=True)
                return []
            a.pop("lost_since", None)
            if t.get("error") != "ok":
                self.abort("Vacuum error or error reading unavailable", now, latch=True)
                return []
            if a["mode"] != "vacuum" and not t.get("wet_ok", False):
                self.abort("Water system needs attention", now, latch=True)
                return []
            if a["phase"] == "preparing":
                self.wait_reason = "Setting cleaning mode"
                if t.get("mode") == a["mode"]:
                    if a["mode"] != "vacuum" and cfg.get("mop_intensity_entity"):
                        if t.get("mop_intensity") != cfg["mop_intensity"]:
                            if not a.get("water_setting_sent"):
                                a["water_setting_sent"] = True
                                return [{"kind": "set_water", "option": cfg["mop_intensity"]}]
                            if now - a["phase_at"] > cfg["start_timeout"]:
                                self.fault_effect("set_water", "Water intensity did not confirm", now)
                            return []
                    a.update(phase="starting", phase_at=now, command_at=now,
                             baseline_record=[(t.get("record") or {}).get("begin"), (t.get("record") or {}).get("end")],
                             baseline_empty_count=t.get("empty_count"))
                    effects.append({"kind": "clean", "segments": a["segments"], "area_id": a["area_id"]})
                elif now - a["phase_at"] > cfg["start_timeout"]:
                    self.fault_effect("set_mode", "Requested mode did not confirm", now)
                return effects
            if t.get("vacuum") == "cleaning":
                a["seen_cleaning"] = True
                if a["phase"] == "starting":
                    a.update(phase="cleaning", phase_at=now)
            if a.get("command_at") and t.get("emptying") is True:
                a["empty_seen"] = True
            if a.get("empty_seen") and t.get("emptying") is False:
                a["empty_finished"] = True
            record = t.get("record") or {}
            matches = self.record_matches(a, record, now)
            if matches and a.get("seen_cleaning") and self.record_success(record):
                a["proved"] = True
                a["record"] = record
            if a.get("proved") and a.get("baseline_empty_count") is not None and t.get("empty_count") is not None:
                if t["empty_count"] > a["baseline_empty_count"]:
                    a["empty_finished"] = True
            if a.get("proved") and t.get("vacuum") == "idle" and not a.get("finish_dock_sent"):
                a["finish_dock_sent"] = True
                return [{"kind": "dock"}]
            if a["phase"] in ("starting", "cleaning", "verifying"):
                self.wait_reason = "Cleaning " + a["name"]
                if a["phase"] == "starting" and now - a["command_at"] > cfg["start_timeout"]:
                    self.abort("Dobby never confirmed cleaning; check the command/map", now, latch=True)
                    return []
                if now - a["command_at"] > cfg["room_timeout"]:
                    self.abort("Room time limit reached", now, latch=True)
                    return []
                if t.get("vacuum") == "docked" and a.get("seen_cleaning"):
                    if t.get("washing") is True and not a.get("proved"):
                        a.pop("docked_since", None)
                        self.wait_reason = "Mop washing during the job; room is not complete"
                        return []
                    a.setdefault("docked_since", now)
                    self.wait_reason = "Checking completed-clean record and dock service"
                    if not a.get("proved"):
                        if now - a["docked_since"] > cfg["proof_timeout"]:
                            if matches and record.get("complete") in (False, 0) and t.get("battery", 100) < cfg["minimum_battery"]:
                                j = self.find(a["uid"])
                                if j:
                                    j["reason"] = "Incomplete low-battery run; retry after charging"
                                self.active = None
                            else:
                                self.fault_effect("completion", "Docked without a confirmed successful clean. Retry or manually confirm after checking.", now)
                        return []
                    if t.get("washing") is None:
                        self.wait_reason = "Mop-wash state unavailable"
                        return []
                    if t.get("washing") or t.get("emptying"):
                        return []
                    if now - a["docked_since"] < cfg["dock_settle"]:
                        return []
                    needs_empty = cfg["empty_after_room"] and (a["mode"] != "mop" or cfg["empty_after_mop"])
                    if needs_empty and not a.get("empty_finished"):
                        a.update(phase="emptying", phase_at=now)
                        return [{"kind": "empty"}]
                    self._complete(now)
                else:
                    a.pop("docked_since", None)
                return []
            if a["phase"] == "emptying":
                self.wait_reason = "Emptying dustbin"
                if t.get("vacuum") != "docked":
                    self.abort("Dobby left the dock before emptying finished", now, latch=True)
                elif a.get("empty_finished") and t.get("emptying") is False and t.get("washing") is False:
                    self._complete(now)
                elif now - a["phase_at"] > cfg["empty_timeout"]:
                    self.fault_effect("empty", "No observed dust-emptying on/off cycle. Check DND and the dock, then Retry.", now)
                return []
            return []
        if self.fault:
            self.wait_reason = self.fault
            return []
        if not (self.enabled or self.manual):
            self.wait_reason = "Scheduler disabled"
            return []
        if not in_window(local_now, cfg["window_start"], cfg["window_end"]):
            self.wait_reason = "Outside the cleaning window"
            return []
        if home is None:
            self.wait_reason = "Home presence unavailable"
            return []
        if home and not self.allow_home:
            self.wait_reason = "Waiting for everyone to leave"
            return []
        if not self.manual and (self.away_since is None or now - self.away_since < cfg["away_minutes"] * 60):
            self.wait_reason = "Waiting for the away delay"
            return []
        j = next((j for j in self.jobs if j["status"] == "needs_action"), None)
        if not j:
            self.manual = self.allow_home = False
            self.wait_reason = "Today's queue is complete"
            return []
        r = rooms.get(j["area_id"])
        error = self._preflight(t, cfg, r)
        if error:
            self.wait_reason = error
            return []
        self.active = {"uid": j["uid"], "area_id": r["area_id"], "name": r["name"],
                       "mode": r["mode"], "map_name": r["map_name"], "map_flag": r["map_flag"],
                       "segments": r["segments"], "phase": "preparing", "phase_at": now,
                       "command_at": None, "seen_cleaning": False, "proved": False,
                       "interrupted": False, "empty_seen": False, "empty_finished": False,
                       "start_timeout": cfg["start_timeout"]}
        self.note(f"Starting {r['name']} ({r['mode']})", now)
        self.wait_reason = "Setting cleaning mode"
        return [{"kind": "set_mode", "option": r["mode"]}]

    def _complete(self, now):
        a = self.active
        j = self.find(a["uid"])
        if j:
            j.update(status="completed", completed_at=now,
                     reason="Successful clean record + dock + required emptying confirmed")
        self.note("Completed " + a["name"], now)
        self.active = None

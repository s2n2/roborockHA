"""Read-only activity presentation and room debounce; no robot commands or HA I/O.

The reported location must remain unchanged for the whole confirmation interval.
Room timers use monotonic time, are not restored, and never prove job completion.
An unconfirmed owned-job target may appear with an arrow, never as measured location.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any

MISSING = {"", "none", "unknown", "unavailable", "null", "not_available", "unknown_room", "not_in_a_room", "unmapped"}
NO_ERROR = MISSING | {"ok", "no_error", "no_errors", "0", "normal"}
CLEANING = {"cleaning", "segment_cleaning", "room_cleaning", "zoned_cleaning", "spot_cleaning", "cleaning_by_room", "selective_room_cleaning", "zone_cleaning", "vacuuming", "mopping"}
RETURNING = {"returning", "returning_home", "returning_to_dock", "returning_to_charge", "back_to_dock", "going_to_dock", "docking", "returning_to_wash", "going_to_wash_the_mop", "going_to_wash"}
WASHING = {"washing", "washing_mop", "mop_washing", "washing_the_mop"}
EMPTYING = {"emptying", "dust_collecting", "dust_collection", "emptying_the_bin", "emptying_the_container", "collecting_dust"}
DRYING = {"drying", "drying_mop", "mop_drying", "drying_the_mop"}
DOCKED = {"docked", "charging", "charging_complete", "fully_charged", "charge_complete"}


def token(value: Any) -> str:
    return re.sub(r"[\s-]+", "_", str(value or "").strip().casefold())


def humanize(value: Any) -> str:
    text = str(value or "").strip().replace("_", " ")
    return (text[:1].upper() + text[1:])[:200]


def error_message(value: Any) -> str | None:
    return humanize(value) if token(value) not in NO_ERROR else None


def resolve_room(raw: Any, maps: list[dict], current_map: str) -> str | None:
    """Keep named readings; resolve numerical segments only on an identified map."""
    text = str(raw or "").strip()
    if token(text) in MISSING:
        return None
    if re.fullmatch(r"-?\d+(?:\.0+)?", text):
        segment = int(float(text))
        if segment <= 0:
            return None
        matching = [m for m in maps if str(m.get("name")) == str(current_map) or str(m.get("flag")) == str(current_map)]
        if len(matching) != 1:
            return None
        value = matching[0].get("rooms", {}).get(str(segment))
        return humanize(value) if value and token(value) not in MISSING else None
    return humanize(text)


@dataclass
class RoomDebouncer:
    candidate: str | None = None
    since: float | None = None
    confirmed: str | None = None
    confirmed_at: float | None = None

    def reset(self) -> None:
        self.candidate = self.since = self.confirmed = self.confirmed_at = None

    def feed(self, room: str | None, now: float, seconds: float) -> None:
        if room is None:
            self.reset()
            return
        if room != self.candidate or self.since is None or now < self.since:
            self.candidate, self.since = room, now
        if now - self.since >= seconds and room != self.confirmed:
            self.confirmed, self.confirmed_at = room, now


def classify(data: dict) -> tuple[str, str, str]:
    """Return code, readable text, icon. Physical telemetry wins over the queue."""
    v, detail = token(data.get("vacuum_state")), token(data.get("detail_state"))
    if not data.get("vacuum_entity"):
        return "not_configured", "Not configured", "mdi:cog-outline"
    if v in MISSING:
        return "unavailable", "Unavailable", "mdi:robot-vacuum-off"
    if message := error_message(data.get("error_raw")):
        return "error", message, "mdi:alert-circle-outline"
    if message := error_message(data.get("dock_error_raw")):
        return "dock_error", message, "mdi:alert-circle-outline"
    if v == "error" or detail in {"error", "device_error", "in_error"}:
        return "error", "Vacuum error", "mdi:alert-circle-outline"
    # Native movement/paused states take precedence over asynchronously updated
    # detail sensors. Specific details can refine CLEANING (e.g. a go-to command)
    # and DOCKED (washing/emptying/charging), but cannot contradict them.
    if v == "paused":
        return "paused", "Paused", "mdi:pause-circle-outline"
    if v in RETURNING or (v in {"idle", "standby"} and detail in RETURNING):
        return "returning", "Returning to dock", "mdi:home-import-outline"
    if v in CLEANING | {"idle", "standby"}:
        if detail in {"going_to_target", "going_to_goal", "going_to_position"}:
            return "moving", "Moving to target", "mdi:map-marker-path"
        if detail in {"mapping", "building_map", "fast_mapping"}:
            return "mapping", "Mapping", "mdi:map-outline"
    if v in DOCKED | {"idle", "standby"}:
        if detail in EMPTYING or data.get("emptying") is True:
            return "emptying", "Emptying dustbin", "mdi:delete-empty-outline"
        if detail in WASHING or data.get("washing") is True:
            return "washing_mop", "Washing mop", "mdi:water-sync"
        if detail == "attaching_the_mop":
            return "attaching_mop", "Attaching mop", "mdi:robot-vacuum"
        if detail == "detaching_the_mop":
            return "detaching_mop", "Detaching mop", "mdi:robot-vacuum"
        if detail == "updating":
            return "updating", "Updating firmware", "mdi:update"
    if v in CLEANING or (v in {"idle", "standby"} and detail in CLEANING):
        mode = token(data.get("mode"))
        if mode == "mop":
            return "mopping", "Mopping", "mdi:water"
        if mode == "vac_and_mop":
            return "vacuuming_and_mopping", "Vacuuming and mopping", "mdi:robot-vacuum"
        # A custom room mode is not assumed to be vacuum-only.
        return "cleaning", "Cleaning", "mdi:robot-vacuum"
    if v == "paused" or detail == "paused":
        return "paused", "Paused", "mdi:pause-circle-outline"
    if detail in {"going_to_target", "going_to_goal", "going_to_position"}:
        return "moving", "Moving to target", "mdi:map-marker-path"
    if detail in {"mapping", "building_map", "fast_mapping"}:
        return "mapping", "Mapping", "mdi:map-outline"
    if v in DOCKED and (detail in DRYING or data.get("drying") is True):
        return "drying_mop", "Drying mop", "mdi:weather-windy"
    if v in DOCKED:
        if data.get("water_problems"):
            return "water_attention", data["water_problems"][0], "mdi:water-alert-outline"
        if v == "charging" or detail == "charging":
            return "charging", "Charging", "mdi:battery-charging"
        return "docked", "Docked", "mdi:home-map-marker"
    if v in {"idle", "standby", "sleeping", "off"}:
        return "idle", "Idle", "mdi:robot-vacuum"
    return "other", humanize(data.get("vacuum_state")) or "Unknown status", "mdi:robot-vacuum"


class ActivityTracker:
    """Two independent latches: last observed location and this cleaning spell.

Location can be confirmed while idle too. The activity's cleaning room starts a
fresh window on each cleaning spell; a previous job's room never becomes a new
job's location just because a queue entry or stale map sensor says so.
"""
    def __init__(self) -> None:
        self.location = RoomDebouncer()
        self.cleaning_location = RoomDebouncer()
        self.context = None
        self.cleaning_run = None

    def update(self, data: dict, now: float, seconds: float = 60) -> dict:
        seconds = float(seconds)
        if not math.isfinite(seconds) or not 1 <= seconds <= 600:
            seconds = 60.0
        identity = (data.get("vacuum_entity"), data.get("room_source"), data.get("map_name"), seconds)
        if identity != self.context:
            self.location.reset()
            self.cleaning_location.reset()
            self.context = identity
        code, text, icon = classify(data)
        detail_text = text
        # Keep activity_code stable for existing automations; shorten only display.
        text = {
            "vacuuming_and_mopping": "Vac + mop",
            "returning": "Returning",
            "emptying": "Emptying",
            "moving": "Moving",
            "updating": "Updating",
        }.get(code, text)
        if code == "cleaning" and token(data.get("mode")) == "vacuum":
            text = "Vacuuming"
        valid = code not in {"unavailable", "not_configured"}
        room = data.get("resolved_room") if valid else None
        self.location.feed(room, now, seconds)
        display_room = display_room_source = None
        if code in {"cleaning", "mopping", "vacuuming_and_mopping"}:
            # A new dispatched attempt must not inherit the preceding job's room,
            # even when a short dock visit was missed between telemetry updates.
            run = data.get("scheduled_run_id")
            if run != self.cleaning_run:
                self.cleaning_location.reset()
                self.cleaning_run = run
            self.cleaning_location.feed(room, now, seconds)
            if self.cleaning_location.confirmed:
                display_room = self.cleaning_location.confirmed
                display_room_source = "confirmed"
                text += " \u00b7 " + display_room
                detail_text += " " + display_room
            elif run and token(data.get("scheduled_room")) not in MISSING:
                # The adapter only passes a dispatched, non-interrupted owned job.
                # Arrow means target/job, not a claim of physical presence there.
                display_room = humanize(data["scheduled_room"])
                display_room_source = "scheduled"
                text += " \u2192 " + display_room
                detail_text += " (scheduled room: " + display_room + ")"
        else:
            self.cleaning_location.reset()
            self.cleaning_run = None
        actual_room = self.cleaning_location.confirmed
        return {
            "text": text[:250], "detail_text": detail_text[:250],
            "display_room": display_room, "display_room_source": display_room_source,
            "code": code, "icon": icon, "available": code != "unavailable",
            "room": actual_room, "room_is_current": bool(actual_room and room == actual_room),
            "confirmed_room": self.location.confirmed,
            "confirmed_room_is_current": bool(self.location.confirmed and self.location.confirmed == room),
            "candidate_room": room, "room_available": bool(valid and room),
            "room_pending": bool(room and (actual_room != room if code in {"cleaning", "mopping", "vacuuming_and_mopping"} else self.location.confirmed != room)),
            "confirmation_seconds": seconds,
        }

"""Home Assistant adapter for the Dobby queue.

Uses HA's existing Roborock connection. No credentials, direct robot protocol,
HTTP downloads, shell commands, or additional Python packages are involved.
"""
from __future__ import annotations
import asyncio
from copy import deepcopy
from datetime import timedelta
import logging
import time

from homeassistant.core import Context, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er, label_registry as lr
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .engine import Engine, GestureDetector, DEFAULTS, resolve_mode, validate_segments, number, clock_minutes, cleaning_day

DOMAIN = "dobby_scheduler"
_LOGGER = logging.getLogger(__name__)
LABELS = {
    "dobby_cleanable": "Include this Home Assistant Area in Dobby's room picker.",
    "dobby_daily": "Add this Area to the queue at the nightly reset.",
    "dobby_vacuum": "Vacuum only. Use just one Dobby mode label on each Area.",
    "dobby_vacuum_mop": "Vacuum and mop. Use just one Dobby mode label on each Area.",
    "dobby_mop": "Mop only. Use just one Dobby mode label on each Area.",
    "dobby_room_toggle": "Four on/off changes in two seconds queue this entity's Area next. Label ONE physical input entity, not its mirrored light as well.",
}
LEGACY_NAMES = {
    "Dobby - Clean daily when noone is home", "Dobby - Go back to dock when we arrive home",
    "Dobby has done cleaning today, don't clean again", "Dobby - new day, reset him to clean today",
    "Reset Dobbys map to saved one",
}
LEGACY_IDS = {"1724537369968", "1724537691707", "1724629183182", "1724629252829", "1724881864606"}


def getfield(obj, key, default=None):
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def error_value(state):
    return "ok" if str(state).casefold() in ("none", "ok", "no_error", "0") else "problem"


def normalize_record(record):
    if record is None:
        return None
    data = {k: getfield(record, k) for k in ("begin", "end", "complete", "error", "area", "map_flag")}
    for k, value in list(data.items()):
        if hasattr(value, "value"):
            data[k] = value.value
    return data


def normalize_maps(response, vacuum):
    body = response.get(vacuum, response) if isinstance(response, dict) else {}
    items = body.get("maps", []) if isinstance(body, dict) else []
    out = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("rooms"), dict):
            continue
        flag = number(item.get("flag"))
        if flag is None or flag != int(flag):
            continue
        rooms = {}
        for key, value in item["rooms"].items():
            n = number(key)
            if n is not None and n == int(n) and n > 0:
                rooms[str(int(n))] = str(value)
        out.append({"flag": int(flag), "name": str(item.get("name", "")), "rooms": rooms})
    return out


class DobbyController:
    def __init__(self, hass, entry):
        self.hass, self.entry = hass, entry
        self.store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self.engine = Engine()
        self.settings = deepcopy(DEFAULTS)
        self.room_config = {}
        self.maps = []
        self.maps_at = None
        self.rooms = {}
        self.toggle_entities = {}
        self.gestures = GestureDetector()
        self.listeners = set()
        self.unsubs = []
        self.lock = asyncio.Lock()
        self.tick_pending = False
        self.stopped = False
        self.own_contexts = set()
        self.queue_entity_id = None
        self.entities = {}
        self.backend_detail = "Not checked"
        self.last_telemetry = {}
        self.registry_revision = 0
        self._saved_data = None

    async def async_load(self):
        saved = await self.store.async_load() or {}
        self.settings.update({k: v for k, v in saved.get("settings", {}).items() if k in DEFAULTS})
        self.room_config = saved.get("rooms", {})
        self.maps, self.maps_at = saved.get("maps", []), saved.get("maps_at")
        self.engine = Engine(saved.get("engine"))
        self.refresh_registry()
        self.unsubs += [
            self.hass.bus.async_listen("state_changed", self._state_changed),
            self.hass.bus.async_listen("call_service", self._service_called),
            self.hass.bus.async_listen("area_registry_updated", self._registry_changed),
            self.hass.bus.async_listen("entity_registry_updated", self._registry_changed),
            self.hass.bus.async_listen("device_registry_updated", self._registry_changed),
            self.hass.bus.async_listen("label_registry_updated", self._registry_changed),
            async_track_time_interval(self.hass, self._timer, timedelta(seconds=5)),
        ]
        self.kick()

    async def async_unload(self):
        self.stopped = True
        for unsub in self.unsubs:
            unsub()
        self.unsubs = []
        async with self.lock:
            await self.persist()
        # An owned in-progress job is preserved for conservative recovery on reload.

    def add_listener(self, fn):
        self.listeners.add(fn)
        return lambda: self.listeners.discard(fn)

    @callback
    def publish(self):
        for fn in tuple(self.listeners):
            fn()

    def raw(self, entity):
        s = self.hass.states.get(entity) if entity else None
        return s.state if s else "unknown"

    def boolean(self, entity, absent=False):
        if not entity:
            return absent
        return {"on": True, "off": False}.get(self.raw(entity))

    def label_ids(self):
        reg = lr.async_get(self.hass)
        out = {}
        for canonical in LABELS:
            item = reg.async_get_label(canonical) or reg.async_get_label_by_name(canonical)
            if item:
                out[canonical] = item.label_id
        return out

    @callback
    def refresh_registry(self):
        labels = self.label_ids()
        areas = ar.async_get(self.hass)
        entities = er.async_get(self.hass)
        devices = dr.async_get(self.hass)
        self.rooms = {}
        for a in areas.areas.values():
            canonical = {k for k, v in labels.items() if v in a.labels}
            mode, warning = resolve_mode(canonical)
            conf = self.room_config.get(a.id, {})
            mapped = next((m for m in self.maps if m["flag"] == conf.get("map_flag")), None)
            segments = conf.get("segments", [])
            mapping_error = ""
            if conf.get("verified"):
                if not mapped or mapped["name"] != conf.get("map_name"):
                    mapping_error = "Saved map no longer matches fetched maps; verify mapping"
                elif any(str(n) not in mapped["rooms"] for n in segments):
                    mapping_error = "A saved segment is missing from the fetched map"
                elif conf.get("verified_names") != {str(n): mapped["rooms"].get(str(n)) for n in segments}:
                    mapping_error = "Mapped room names changed; re-check this mapping"
            self.rooms[a.id] = {
                "area_id": a.id, "name": a.name,
                "cleanable": "dobby_cleanable" in canonical,
                "daily": "dobby_daily" in canonical,
                "mode": mode, "mode_label": next((k for k in ("dobby_vacuum", "dobby_vacuum_mop", "dobby_mop") if k in canonical), ""),
                "mode_warning": warning, "priority": conf.get("priority", 100),
                "segments": segments, "map_flag": conf.get("map_flag"),
                "map_name": conf.get("map_name", ""), "verified": conf.get("verified", False),
                "mapping_error": mapping_error,
            }
        # Even when names match, overlapping segments cannot count as distinct rooms.
        used = {}
        for r in self.rooms.values():
            if not r["cleanable"]:
                continue
            for n in r["segments"]:
                key = (r["map_flag"], n)
                if key in used:
                    other = self.rooms[used[key]]
                    r["mapping_error"] = f"Segment {n} is also assigned to {other['name']}"
                    other["mapping_error"] = f"Segment {n} is also assigned to {r['name']}"
                used[key] = r["area_id"]
        self.toggle_entities = {}
        for e in entities.entities.values():
            if e.disabled_by or labels.get("dobby_room_toggle") not in e.labels:
                continue
            if e.entity_id.split(".")[0] not in ("switch", "light", "binary_sensor", "input_boolean"):
                continue
            device = devices.async_get(e.device_id) if e.device_id else None
            self.toggle_entities[e.entity_id] = e.area_id or (device.area_id if device else None)
        self.registry_revision += 1

    @callback
    def _registry_changed(self, event):
        self.refresh_registry()
        self.publish()
        self.kick()

    @callback
    def _state_changed(self, event):
        entity = event.data.get("entity_id")
        old, new = event.data.get("old_state"), event.data.get("new_state")
        if entity in self.toggle_entities and old and new:
            if self.gestures.feed(entity, old.state, new.state, time.monotonic(),
                                 self.settings["gesture_seconds"], self.settings["gesture_cooldown"],
                                 automation=bool(new.context.parent_id),
                                 reject_automation=self.settings["reject_automation_context"]):
                self.hass.async_create_task(self._gesture(entity))
        watched = {v for k, v in self.settings.items() if k.endswith("_entity") and isinstance(v, str)}
        watched.update(self.settings["water_problem_entities"] + self.settings["blocking_entities"])
        if entity in watched or (entity or "").startswith("automation."):
            self.kick()

    @callback
    def _service_called(self, event):
        """Another HA vacuum command invalidates ownership. App commands are not observable here."""
        if not self.engine.active or event.context.id in self.own_contexts:
            return
        data = event.data
        if data.get("domain") != "vacuum" or data.get("service") not in (
            "start", "stop", "pause", "return_to_base", "clean_area", "send_command", "clean_spot"
        ):
            return
        target = data.get("service_data", {}).get("entity_id", [])
        if isinstance(target, str):
            target = [target]
        if self.settings["vacuum_entity"] in target:
            self.hass.async_create_task(self._external_interference())

    async def _external_interference(self):
        async with self.lock:
            self.engine.abort("Another Home Assistant command interrupted the job", time.time(), latch=True)
            await self.persist()
        self.kick()

    async def _gesture(self, entity):
        area = self.toggle_entities.get(entity)
        async with self.lock:
            if not area or not self.rooms.get(area, {}).get("cleanable"):
                self.engine.note(f"Ignored gesture on {entity}: no cleanable Area", time.time())
                await self.persist()
                self.publish()
                return
            self.engine.enqueue(area, self.rooms, time.time(), urgent=True, source="wall_toggle")
            await self.persist()
            self.publish()
        # Acknowledgement is deliberately outside the queue lock.
        if self.settings["acknowledge"] and self.settings["vacuum_entity"]:
            try:
                await self.call("vacuum", "locate", self.settings["vacuum_entity"])
            except HomeAssistantError:
                _LOGGER.info("Room was queued, but Locate acknowledgement failed")
        self.kick()

    @callback
    def _timer(self, now):
        self.kick()

    @callback
    def kick(self):
        if not self.stopped and not self.tick_pending:
            self.tick_pending = True
            self.hass.async_create_task(self.async_tick())

    def legacy(self):
        return [{"entity_id": s.entity_id, "name": s.attributes.get("friendly_name", s.entity_id)}
                for s in self.hass.states.async_all("automation")
                if s.state == "on" and (s.attributes.get("friendly_name") in LEGACY_NAMES or
                                        str(s.attributes.get("id")) in LEGACY_IDS)]

    def _coordinator(self):
        """Guarded, read-only compatibility adapter; never invokes private commands.

HA has no public completed-success service. Current official Roborock V1 exposes
this record through its coordinator. Any incompatible layout fails closed.
"""
        component = self.hass.data.get("vacuum")
        getter = getattr(component, "get_entity", None)
        entity = getter(self.settings["vacuum_entity"]) if getter else None
        if entity is not None:
            return getattr(entity, "coordinator", None)
        # Config-entry fallback uses device identifiers, not a guessed first robot.
        ent = er.async_get(self.hass).async_get(self.settings["vacuum_entity"])
        if not ent or not ent.config_entry_id or not ent.device_id:
            return None
        dev = dr.async_get(self.hass).async_get(ent.device_id)
        entry = self.hass.config_entries.async_get_entry(ent.config_entry_id)
        runtime = getattr(entry, "runtime_data", None) if entry else None
        values = getattr(runtime, "values", None)
        if not values or not dev:
            return None
        for coordinator in values():
            info = getattr(coordinator, "device_info", {})
            if set(info.get("identifiers", [])) & set(dev.identifiers):
                return coordinator
        return None

    def clean_record(self):
        external = self.settings.get("completion_entity")
        if external:
            state = self.hass.states.get(external)
            if state and state.state not in ("unknown", "unavailable"):
                rec = normalize_record(state.attributes)
                supported = all(k in state.attributes for k in ("begin", "end", "complete", "error", "area"))
                self.backend_detail = "Configured success-record entity" if supported else "Configured entity lacks complete/error/begin/end/area attributes"
                return rec, supported, None
            self.backend_detail = "Configured completed-record sensor unavailable"
            return None, False, None
        coordinator = self._coordinator()
        data = getattr(coordinator, "data", None)
        summary = getfield(data, "clean_summary")
        if summary is None:
            props = getattr(coordinator, "properties_api", None)
            summary = getattr(props, "clean_summary", None)
        if summary is None:
            self.backend_detail = "Official Roborock V1 completed-record adapter not available"
            return None, False, None
        missing = object()
        record = getfield(summary, "last_clean_record", missing)
        if record is missing:
            self.backend_detail = "Completed-clean record field missing; adapter incompatible"
            return None, False, None
        supported = record is None or all(getfield(record, k, "__absent__") != "__absent__" for k in ("begin", "end", "complete", "error", "area"))
        self.backend_detail = "Read-only Roborock V1 completed-clean record" if supported else "Unsupported record fields; automatic completion is blocked"
        props = getattr(coordinator, "properties_api", None)
        flag = getfield(getattr(props, "maps", None), "current_map")
        return normalize_record(record), supported, flag

    def _empty_count(self):
        coordinator = self._coordinator()
        summary = getfield(getattr(coordinator, "data", None), "clean_summary")
        if summary is None:
            summary = getattr(getattr(coordinator, "properties_api", None), "clean_summary", None)
        return number(getfield(summary, "dust_collection_count"))

    def telemetry(self):
        c = self.settings
        state = self.hass.states.get(c["vacuum_entity"]) if c["vacuum_entity"] else None
        mode_state = self.hass.states.get(c["mode_entity"]) if c["mode_entity"] else None
        record, supported, flag = self.clean_record()
        battery = number(self.raw(c["battery_entity"]))
        if battery is None and state:
            battery = number(state.attributes.get("battery_level"))
        map_name = self.raw(c["map_entity"])
        if not c["map_entity"] and flag is not None:
            map_name = next((m["name"] for m in self.maps if str(m["flag"]) == str(flag)), "unknown")
        t = {"now": time.time(), "home": self.boolean(c["presence_entity"], absent=None),
             "vacuum": state.state if state else "unknown", "connected": bool(state and state.state not in ("unknown", "unavailable")),
             "mode": mode_state.state if mode_state else "unknown", "mode_options": list(mode_state.attributes.get("options", [])) if mode_state else [],
             "battery": battery, "error": error_value(self.raw(c["error_entity"])),
             "map_name": map_name, "map_flag": flag,
             "emptying": self.boolean(c["empty_entity"], absent=None),
             "washing": self.boolean(c["wash_entity"], absent=False),
             "wet_ok": all(self.boolean(e, absent=None) is False for e in c["water_problem_entities"]),
             "blockers": any(self.boolean(e, absent=None) is not False for e in c["blocking_entities"]),
             "record": record, "record_supported": supported, "legacy": self.legacy(),
             "mop_intensity": self.raw(c["mop_intensity_entity"]),
             "empty_count": self._empty_count()}
        self.last_telemetry = t
        return t

    async def async_tick(self):
        try:
            async with self.lock:
                if self.stopped:
                    return
                t = self.telemetry()
                effects = self.engine.tick(t, self.settings, self.rooms, dt_util.now())
                await self.persist()  # Commit intent before issuing any robot command.
                self.publish()
                for effect in effects:
                    try:
                        await self.execute(effect)
                    except Exception as err:
                        _LOGGER.warning("Dobby %s action failed: %s", effect["kind"], err)
                        self.engine.fault_effect(effect["kind"], str(err), time.time())
                        await self.persist()
                        self.publish()
                        break
        except Exception as err:
            _LOGGER.exception("Dobby scheduler paused after an internal error")
            self.engine.fault_effect("scheduler", str(err), time.time())
            self.engine.enabled = False
            await self.persist()
            self.publish()
        finally:
            self.tick_pending = False

    async def call(self, domain, service, entity, **data):
        if not entity:
            raise HomeAssistantError("Required control entity is not configured")
        context = Context()
        self.own_contexts.add(context.id)
        if len(self.own_contexts) > 300:
            self.own_contexts = {context.id}
        # No arbitrary user-supplied domain/service names reach this method.
        async with asyncio.timeout(45):
            return await self.hass.services.async_call(domain, service, {"entity_id": entity, **data}, blocking=True, context=context)

    async def execute(self, effect):
        c, kind = self.settings, effect["kind"]
        if kind == "set_mode":
            await self.call("select", "select_option", c["mode_entity"], option=effect["option"])
        elif kind == "set_water":
            await self.call("select", "select_option", c["mop_intensity_entity"], option=effect["option"])
        elif kind == "clean":
            # Explicit approved map/segment command avoids a second hidden HA mapping.
            await self.call("vacuum", "send_command", c["vacuum_entity"], command="app_segment_clean", params=[{"segments": effect["segments"], "repeat": 1}])
        elif kind == "dock":
            await self.call("vacuum", "return_to_base", c["vacuum_entity"])
        elif kind == "empty":
            await self.call("switch", "turn_on", c["empty_entity"])

    async def persist(self):
        data = {"settings": self.settings, "rooms": self.room_config, "maps": self.maps,
                "maps_at": self.maps_at, "engine": self.engine.export()}
        if data != self._saved_data:
            await self.store.async_save(data)
            self._saved_data = deepcopy(data)

    def snapshot(self, include_config=False):
        self.telemetry()
        jobs = []
        for j in self.engine.jobs:
            r = self.rooms.get(j["area_id"], {})
            jobs.append({**j, "name": r.get("name", j["area_id"]), "mode": r.get("mode"),
                         "segments": r.get("segments", []), "map_name": r.get("map_name", ""),
                         "priority": r.get("priority", 100), "mapping_error": r.get("mapping_error", "")})
        out = {"version": "0.1.0", "entry_id": self.entry.entry_id, "name": self.entry.title,
               "enabled": self.engine.enabled, "manual": self.engine.manual,
               "active": deepcopy(self.engine.active), "reason": self.engine.wait_reason,
               "fault": self.engine.fault, "day": self.engine.day, "jobs": jobs,
               "rooms": list(self.rooms.values()), "maps": self.maps, "maps_at": self.maps_at,
               "telemetry": self.last_telemetry, "backend": self.backend_detail,
               "labels": self.label_ids(), "toggle_entities": self.toggle_entities,
               "entities": self.entities, "log": self.engine.log[-20:], "reset_deferred": self.engine.reset_deferred,
               "registry_revision": self.registry_revision}
        if include_config:
            out["settings"] = deepcopy(self.settings)
            out["candidates"] = [{"entity_id": s.entity_id, "name": s.attributes.get("friendly_name", s.entity_id),
                                  "state": s.state, "options": s.attributes.get("options", [])}
                                 for s in self.hass.states.async_all()
                                 if s.domain in ("vacuum", "select", "sensor", "switch", "binary_sensor", "input_boolean")]
        return out

    def detect(self, vacuum):
        if not vacuum.startswith("vacuum.") or not self.hass.states.get(vacuum):
            raise ValueError("Select an existing vacuum")
        slug = vacuum.split(".", 1)[1]
        suffix = {"mode_entity": ("select", "cleaning_mode"), "battery_entity": ("sensor", "battery"),
                  "error_entity": ("sensor", "vacuum_error"), "map_entity": ("select", "selected_map"),
                  "empty_entity": ("switch", "dock_dust_emptying"), "wash_entity": ("switch", "dock_mop_washing"),
                  "mop_intensity_entity": ("select", "mop_intensity")}
        out = {"vacuum_entity": vacuum}
        for key, (domain, tail) in suffix.items():
            e = f"{domain}.{slug}_{tail}"
            if self.hass.states.get(e):
                out[key] = e
        out["water_problem_entities"] = [e for tail in ("dock_clean_water_box", "dock_dirty_water_box", "water_shortage")
                                        if self.hass.states.get(e := f"binary_sensor.{slug}_{tail}")]
        if self.hass.states.get("binary_sensor.someone_home"):
            out["presence_entity"] = "binary_sensor.someone_home"
        return out

    async def refresh_maps(self):
        if self.engine.active:
            raise ValueError("Pause and dock Dobby before checking maps")
        vacuum = self.settings["vacuum_entity"]
        if self.raw(vacuum) != "docked":
            raise ValueError("Dock Dobby before checking maps")
        async with asyncio.timeout(60):
            response = await self.hass.services.async_call("roborock", "get_maps", {"entity_id": vacuum}, blocking=True, return_response=True)
        maps = normalize_maps(response, vacuum)
        if not maps:
            raise ValueError("Roborock returned no supported map data")
        self.maps, self.maps_at = maps, time.time()
        self.refresh_registry()
        await self.persist()
        return maps

    def validate_settings(self, proposed):
        out = deepcopy(self.settings)
        for key, value in proposed.items():
            if key not in DEFAULTS:
                raise ValueError(f"Unknown setting: {key}")
            default = DEFAULTS[key]
            if isinstance(default, bool):
                if not isinstance(value, bool):
                    raise ValueError(f"{key} must be true or false")
            elif isinstance(default, (int, float)):
                n = number(value)
                if n is None:
                    raise ValueError(f"{key} must be a finite number")
                ranges = {"away_minutes": (0, 120), "minimum_battery": (10, 100), "gesture_seconds": (0.5, 5), "gesture_cooldown": (2, 30),
                          "start_timeout": (60, 900), "room_timeout": (600, 21600), "dock_timeout": (60, 1800),
                          "proof_timeout": (60, 900), "empty_timeout": (60, 900), "dock_settle": (5, 120)}
                lo, hi = ranges[key]
                if not lo <= n <= hi:
                    raise ValueError(f"{key} must be between {lo} and {hi}")
                value = int(n) if isinstance(default, int) else n
            elif isinstance(default, list):
                if not isinstance(value, list) or len(value) > 30 or any(not isinstance(e, str) or e.split(".")[0] not in ("binary_sensor", "input_boolean", "switch") for e in value):
                    raise ValueError(f"{key} must be a list of boolean entity IDs")
            elif not isinstance(value, str) or len(value) > 255:
                raise ValueError(f"Invalid text for {key}")
            if key in ("window_start", "window_end", "reset_time"):
                clock_minutes(value)
            if key.endswith("_entity") and value:
                expected = {"vacuum_entity": ["vacuum"], "presence_entity": ["binary_sensor", "input_boolean"],
                            "mode_entity": ["select"], "battery_entity": ["sensor"], "error_entity": ["sensor"],
                            "map_entity": ["select"], "empty_entity": ["switch"], "wash_entity": ["switch"],
                            "mop_intensity_entity": ["select"], "completion_entity": ["sensor"]}[key]
                if value.split(".")[0] not in expected:
                    raise ValueError(f"Wrong entity type for {key}")
            out[key] = value
        return out

    async def command(self, action, p=None):
        p = p or {}
        result = None
        async with self.lock:
            now = time.time()
            if action == "create_labels":
                reg = lr.async_get(self.hass)
                for name, description in LABELS.items():
                    if not reg.async_get_label(name) and not reg.async_get_label_by_name(name):
                        reg.async_create(name, description=description, icon="mdi:robot-vacuum")
                self.refresh_registry()
            elif action == "detect":
                return self.detect(p.get("vacuum_entity", ""))
            elif action == "settings":
                if self.engine.active:
                    raise ValueError("Dock and stop the current job before changing connection/settings")
                checked = self.validate_settings(p)
                if checked["vacuum_entity"] != self.settings["vacuum_entity"]:
                    self.maps, self.maps_at = [], None
                    for r in self.room_config.values():
                        r["verified"] = False
                    self.engine.enabled = False
                self.settings = checked
                self.refresh_registry()
            elif action == "maps":
                result = await self.refresh_maps()
            elif action == "default_order":
                if self.engine.active:
                    raise ValueError("Dock Dobby before changing the default order")
                ids = p.get("area_ids", [])
                if not isinstance(ids, list) or len(ids) != len(set(ids)) or any(a not in self.rooms for a in ids):
                    raise ValueError("Invalid default order")
                for i, area in enumerate(ids):
                    self.room_config.setdefault(area, {})["priority"] = (i + 1) * 10
                self.refresh_registry()
            elif action == "save_room":
                area = p.get("area_id")
                if area not in self.rooms:
                    raise ValueError("Home Assistant Area no longer exists")
                if self.engine.active:
                    raise ValueError("Dock Dobby before changing room labels/mappings")
                if len(str(p)) > 12000:
                    raise ValueError("Room configuration too large")
                priority = number(p.get("priority", 100))
                if priority is None or not 0 <= priority <= 10000:
                    raise ValueError("Priority must be 0-10000; lower goes first")
                conf = {"priority": int(priority), "segments": [], "map_flag": None,
                        "map_name": "", "verified": False, "verified_names": {}}
                if p.get("segments"):
                    segs = validate_segments(p["segments"])
                    m = next((m for m in self.maps if str(m["flag"]) == str(p.get("map_flag"))), None)
                    if not m or any(str(n) not in m["rooms"] for n in segs):
                        raise ValueError("Fetch maps and select room numbers from that map first")
                    conf.update(segments=segs, map_flag=m["flag"], map_name=m["name"],
                                verified=bool(p.get("verified")), verified_names={str(n): m["rooms"][str(n)] for n in segs})
                mode_label = p.get("mode_label", "")
                if mode_label not in ("", "dobby_vacuum", "dobby_vacuum_mop", "dobby_mop"):
                    raise ValueError("Choose one supported cleaning mode")
                labels = self.label_ids()
                if len(labels) != len(LABELS):
                    raise ValueError("Create the Dobby labels first")
                reg = ar.async_get(self.hass)
                a = reg.async_get_area(area)
                keep = set(a.labels) - {labels[k] for k in LABELS if k != "dobby_room_toggle"}
                if p.get("cleanable"):
                    keep.add(labels["dobby_cleanable"])
                if p.get("daily"):
                    keep.add(labels["dobby_daily"])
                if mode_label:
                    keep.add(labels[mode_label])
                self.room_config[area] = conf
                reg.async_update(area, labels=keep)
                self.refresh_registry()
            elif action == "set_toggle":
                e = str(p.get("entity_id", ""))
                reg = er.async_get(self.hass)
                item = reg.async_get(e)
                if not item or e.split(".")[0] not in ("switch", "light", "binary_sensor", "input_boolean"):
                    raise ValueError("Select a registered physical on/off input entity")
                label = self.label_ids().get("dobby_room_toggle")
                if not label:
                    raise ValueError("Create Dobby labels first")
                updated = set(item.labels)
                updated.add(label) if p.get("enabled") else updated.discard(label)
                reg.async_update_entity(e, labels=updated)
                self.refresh_registry()
            elif action == "enqueue":
                result = {"uid": self.engine.enqueue(p.get("area_id"), self.rooms, now, urgent=bool(p.get("urgent")), source="dashboard")}
            elif action == "remove":
                self.engine.remove(p.get("uid"))
            elif action == "move":
                self.engine.move(p.get("uid"), p.get("previous_uid"))
            elif action == "reset":
                if self.engine.active:
                    raise ValueError("Wait for the current job to dock before resetting today's list")
                self.engine.reset(cleaning_day(dt_util.now(), self.settings["reset_time"]), self.rooms, now)
            elif action == "enable":
                self.engine.enabled = bool(p.get("enabled"))
                if not self.engine.enabled:
                    self.engine.abort("Scheduler paused by user", now)
            elif action == "run":
                self.engine.manual = True
                self.engine.allow_home = bool(p.get("allow_home", False))
            elif action == "pause":
                self.engine.enabled = False
                self.engine.abort("Paused and sent to dock by user", now)
                if not self.engine.active and self.raw(self.settings["vacuum_entity"]) not in ("unknown", "unavailable", "docked"):
                    await self.execute({"kind": "dock"})
            elif action == "retry":
                self.engine.retry(now, self.raw(self.settings["vacuum_entity"]) == "docked")
            elif action == "complete":
                self.engine.manual_complete(p.get("uid"), now, self.raw(self.settings["vacuum_entity"]) == "docked")
            elif action == "update_note":
                job = self.engine.find(p.get("uid"))
                if not job:
                    raise ValueError("Queue item no longer exists")
                job["note"] = str(p.get("note", ""))[:2000]
            elif action == "disable_legacy":
                for old in self.legacy():
                    await self.call("automation", "turn_off", old["entity_id"], stop_actions=True)
            elif action == "locate":
                await self.call("vacuum", "locate", self.settings["vacuum_entity"])
            else:
                raise ValueError("Unsupported Dobby command")
            await self.persist()
            self.publish()
        self.kick()
        return result or {"ok": True}

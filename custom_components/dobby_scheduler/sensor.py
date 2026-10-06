"""Status and queue-count entities reusable outside the bundled card."""
from homeassistant.components.sensor import SensorEntity
from .entity import DobbyEntity

async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    async_add_entities([DobbyStatus(c), DobbyCount(c, False), DobbyCount(c, True), DobbyActivity(c), DobbyStableRoom(c)])

class DobbyStatus(DobbyEntity, SensorEntity):
    _attr_icon = "mdi:robot-vacuum"
    def __init__(self, c):
        super().__init__(c, "status", "Status", "sensor")
    @property
    def native_value(self):
        e = self.controller.engine
        return "attention" if e.fault else (e.active["phase"] if e.active else "waiting" if e.enabled or e.manual or e.immediate_jobs() else "disabled")
    @property
    def extra_state_attributes(self):
        c = self.controller
        return {"reason": c.engine.wait_reason, "current_room": (c.engine.active or {}).get("name"),
                "next_room": next((c.rooms.get(j["area_id"], {}).get("name", j["area_id"]) for j in c.engine.jobs
                                  if j["status"] == "needs_action" and j["uid"] != (c.engine.active or {}).get("uid")), None),
                "cleaning_day": c.engine.day, "fault": c.engine.fault, "backend": c.backend_detail,
                "reset_deferred": c.engine.reset_deferred,
                "immediate_requested_rooms": [c.rooms.get(j["area_id"], {}).get("name", j["area_id"])
                                             for j in c.engine.immediate_jobs()],
                "start_policy": (c.engine.active or {}).get("start_policy"),
                "gesture_start_immediately": c.settings.get("gesture_start_immediately", True),
                "requested_mode": (c.engine.active or {}).get("requested_mode"),
                "effective_mode": (c.engine.active or {}).get("mode"),
                "water_fallback": (c.engine.active or {}).get("water_fallback", False),
                "fallback_reason": (c.engine.active or {}).get("fallback_reason", ""),
                "mopping_skipped_rooms": [c.rooms.get(j["area_id"], {}).get("name", j["area_id"])
                    for j in c.engine.jobs if j["status"] == "completed" and j.get("mopping_skipped")]}

class DobbyCount(DobbyEntity, SensorEntity):
    _attr_icon = "mdi:format-list-checks"
    def __init__(self, c, completed):
        self.completed = completed
        super().__init__(c, "completed" if completed else "pending", "Completed rooms" if completed else "Pending rooms", "sensor")
    @property
    def native_value(self):
        return sum((j["status"] == "completed") == self.completed for j in self.controller.engine.jobs)


class DobbyActivity(DobbyEntity, SensorEntity):
    """Human-readable robot activity; intentionally distinct from scheduler status."""
    def __init__(self, c):
        super().__init__(c, "activity", "Activity", "sensor")
        c.update_activity()

    @property
    def available(self):
        return self.controller.activity.get("available", True)

    @property
    def icon(self):
        return self.controller.activity.get("icon", "mdi:robot-vacuum")

    @property
    def native_value(self):
        return self.controller.activity.get("text", "Not configured")

    @property
    def extra_state_attributes(self):
        c, a = self.controller, self.controller.activity
        return {
            "activity_code": a.get("code"), "confirmed_room": a.get("room"),
            "display_room": a.get("display_room"),
            "display_room_source": a.get("display_room_source"),
            "detail": a.get("detail_text"),
            "room_is_current": a.get("room_is_current", False),
            "room_pending_confirmation": a.get("room_pending", False),
            "room_confirmation_seconds": a.get("confirmation_seconds", 60),
            "cleaning_mode": a.get("mode"), "error_code": a.get("error_code"),
            "dock_error_code": a.get("dock_error_code"),
            "vacuum_state": a.get("raw_vacuum_state"), "detailed_status": a.get("raw_status"),
            "scheduled_room": (c.engine.active or {}).get("name"),
            "scheduler_phase": (c.engine.active or {}).get("phase"),
            "scheduler_enabled": c.engine.enabled,
            "room_source": a.get("sources", {}).get("current_room_entity"),
            "status_source": a.get("sources", {}).get("status_entity"),
            "water_problems": a.get("water_problems", []),
            "requested_mode": (c.engine.active or {}).get("requested_mode"),
            "effective_mode": (c.engine.active or {}).get("mode"),
            "water_fallback": (c.engine.active or {}).get("water_fallback", False),
            "fallback_reason": (c.engine.active or {}).get("fallback_reason", ""),
        }


class DobbyStableRoom(DobbyEntity, SensorEntity):
    """Last room whose live sensor reading passed the confirmation window."""
    _attr_icon = "mdi:floor-plan"

    def __init__(self, c):
        super().__init__(c, "room_stable", "Confirmed room", "sensor")
        c.update_activity()

    @property
    def available(self):
        return self.controller.activity.get("room_available", False)

    @property
    def native_value(self):
        return self.controller.activity.get("confirmed_room")

    @property
    def extra_state_attributes(self):
        a = self.controller.activity
        return {
            "source_entity": a.get("sources", {}).get("current_room_entity"),
            "confirmation_seconds": a.get("confirmation_seconds", 60),
            "candidate_room": a.get("candidate_room"),
            "matches_current_reading": a.get("confirmed_room_is_current", False),
            "basis": "Last room reported continuously for the confirmation window; not a live map coordinate.",
        }

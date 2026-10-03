"""Status and queue-count entities reusable outside the bundled card."""
from homeassistant.components.sensor import SensorEntity
from .entity import DobbyEntity

async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    async_add_entities([DobbyStatus(c), DobbyCount(c, False), DobbyCount(c, True)])

class DobbyStatus(DobbyEntity, SensorEntity):
    _attr_icon = "mdi:robot-vacuum"
    def __init__(self, c):
        super().__init__(c, "status", "Status", "sensor")
    @property
    def native_value(self):
        e = self.controller.engine
        return "attention" if e.fault else (e.active["phase"] if e.active else "waiting" if e.enabled or e.manual else "disabled")
    @property
    def extra_state_attributes(self):
        c = self.controller
        return {"reason": c.engine.wait_reason, "current_room": (c.engine.active or {}).get("name"),
                "next_room": next((c.rooms.get(j["area_id"], {}).get("name", j["area_id"]) for j in c.engine.jobs
                                  if j["status"] == "needs_action" and j["uid"] != (c.engine.active or {}).get("uid")), None),
                "cleaning_day": c.engine.day, "fault": c.engine.fault, "backend": c.backend_detail,
                "reset_deferred": c.engine.reset_deferred}

class DobbyCount(DobbyEntity, SensorEntity):
    _attr_icon = "mdi:format-list-checks"
    def __init__(self, c, completed):
        self.completed = completed
        super().__init__(c, "completed" if completed else "pending", "Completed rooms" if completed else "Pending rooms", "sensor")
    @property
    def native_value(self):
        return sum((j["status"] == "completed") == self.completed for j in self.controller.engine.jobs)

"""Shared entity behaviour."""
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.device_registry import DeviceInfo
from .controller import DOMAIN

class DobbyEntity(Entity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, controller, key, name, domain):
        self.controller = controller
        self._attr_name = name
        self._attr_unique_id = f"{controller.entry.entry_id}_{key}"
        self.entity_id = f"{domain}.dobby_scheduler_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, controller.entry.entry_id)},
                                            name=controller.entry.title, manufacturer="Dobby Scheduler",
                                            model="Room queue", sw_version="0.1.0")
        self.key = key

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.controller.entities[self.key] = self.entity_id
        self.async_on_remove(self.controller.add_listener(self._changed))

    @callback
    def _changed(self):
        self.async_write_ha_state()

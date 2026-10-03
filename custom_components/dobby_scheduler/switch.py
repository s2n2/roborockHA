"""Automatic scheduling master switch; initially off."""
from homeassistant.components.switch import SwitchEntity
from .entity import DobbyEntity

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([DobbyEnabled(entry.runtime_data)])

class DobbyEnabled(DobbyEntity, SwitchEntity):
    _attr_icon = "mdi:robot-vacuum"
    def __init__(self, c):
        super().__init__(c, "enabled", "Automatic scheduling", "switch")
    @property
    def is_on(self):
        return self.controller.engine.enabled
    async def async_turn_on(self, **kwargs):
        await self.controller.command("enable", {"enabled": True})
    async def async_turn_off(self, **kwargs):
        await self.controller.command("enable", {"enabled": False})

"""Dobby Scheduler: installable bundle with optional one-line YAML bootstrap."""
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import callback
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.helpers import config_validation as cv

from .compat import vol
from .controller import DobbyController, DOMAIN
from .api import register_api

PLATFORMS = ["sensor", "switch", "todo"]
CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): vol.Schema({vol.Optional("name", default="Dobby Scheduler"): cv.string})}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):
    data = hass.data.setdefault(DOMAIN, {})
    if not data.get("api_registered"):
        register_api(hass)
        await hass.http.async_register_static_paths([
            StaticPathConfig("/dobby_scheduler_frontend", str(Path(__file__).parent / "frontend"), False)
        ])
        data["api_registered"] = True
    if DOMAIN in config:
        hass.async_create_task(hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=config[DOMAIN] or {}
        ))
    return True

async def async_setup_entry(hass, entry):
    controller = DobbyController(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = controller
    entry.runtime_data = controller
    await controller.async_load()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass, entry):
    controller = hass.data[DOMAIN][entry.entry_id]
    await controller.async_unload()
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
        return True
    return False

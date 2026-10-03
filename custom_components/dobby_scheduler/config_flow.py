"""One instance, selected/configured in the card, safe-disabled on installation."""
from homeassistant import config_entries
from .compat import vol
from .controller import DOMAIN

class DobbyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title=user_input.get("name", "Dobby Scheduler"), data={})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required("name", default="Dobby Scheduler"): str
        }))

    async def async_step_import(self, user_input):
        return await self.async_step_user(user_input or {"name": "Dobby Scheduler"})

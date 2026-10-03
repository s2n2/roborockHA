"""Authenticated frontend API and restricted automation services."""
from homeassistant.components import websocket_api
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from .compat import vol
from .controller import DOMAIN, DobbyController

ADMIN_ACTIONS = {"create_labels", "detect", "settings", "maps", "save_room", "set_toggle", "disable_legacy", "default_order"}
QUEUE_ACTIONS = {"enqueue", "remove", "move", "reset", "enable", "run", "pause", "retry", "complete", "update_note", "locate"}


def controller(hass, entry_id=None):
    items = hass.data.get(DOMAIN, {})
    if entry_id and isinstance(items.get(entry_id), DobbyController):
        return items[entry_id]
    found = [v for v in items.values() if isinstance(v, DobbyController)]
    if len(found) != 1:
        raise HomeAssistantError("Dobby Scheduler is not loaded. Install the integration and restart Home Assistant.")
    return found[0]


def permitted(user, c, policy):
    return bool(user and (user.is_admin or (c.queue_entity_id and user.permissions.check_entity(c.queue_entity_id, policy))))


@websocket_api.websocket_command({vol.Required("type"): "dobby_scheduler/get", vol.Optional("entry_id"): str, vol.Optional("include_config", default=False): bool})
@websocket_api.async_response
async def ws_get(hass, connection, msg):
    try:
        c = controller(hass, msg.get("entry_id"))
        if not permitted(connection.user, c, "read"):
            connection.send_error(msg["id"], "unauthorized", "No permission to read Dobby's queue")
            return
        connection.send_result(msg["id"], c.snapshot(include_config=msg.get("include_config", False) and connection.user.is_admin))
    except Exception as err:
        connection.send_error(msg["id"], "dobby_error", str(err))


@websocket_api.websocket_command({vol.Required("type"): "dobby_scheduler/command", vol.Optional("entry_id"): str, vol.Required("action"): str, vol.Optional("data", default={}): dict})
@websocket_api.async_response
async def ws_command(hass, connection, msg):
    action = msg["action"]
    try:
        c = controller(hass, msg.get("entry_id"))
        if action not in ADMIN_ACTIONS | QUEUE_ACTIONS:
            raise ValueError("Unknown Dobby action")
        if action in ADMIN_ACTIONS and not connection.user.is_admin:
            connection.send_error(msg["id"], "unauthorized", "An administrator must configure rooms, mappings and labels")
            return
        if action in QUEUE_ACTIONS and not permitted(connection.user, c, "control"):
            connection.send_error(msg["id"], "unauthorized", "No permission to control Dobby's queue")
            return
        result = await c.command(action, msg.get("data"))
        connection.send_result(msg["id"], result)
    except Exception as err:
        connection.send_error(msg["id"], "dobby_error", str(err))


@callback
def register_api(hass):
    websocket_api.async_register_command(hass, ws_get)
    websocket_api.async_register_command(hass, ws_command)
    schemas = {
        "enqueue": vol.Schema({vol.Required("area_id"): str, vol.Optional("urgent", default=False): bool}),
        "run": vol.Schema({vol.Optional("allow_home", default=False): bool}),
        "pause": vol.Schema({}), "reset": vol.Schema({}), "retry": vol.Schema({}),
        "enable": vol.Schema({vol.Required("enabled"): bool}),
    }
    async def handle(call):
        c = controller(hass)
        if call.context.user_id:
            user = await hass.auth.async_get_user(call.context.user_id)
            if not permitted(user, c, "control"):
                raise HomeAssistantError("No permission to control the Dobby queue")
        await c.command(call.service, dict(call.data))
    for service, schema in schemas.items():
        hass.services.async_register(DOMAIN, service, handle, schema=schema)

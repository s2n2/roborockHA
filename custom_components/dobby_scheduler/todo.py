"""Native, persistent, genuinely ordered Home Assistant to-do queue.

Summary/metadata are derived from the Area and labels. Notes are editable;
metadata cannot be used to bypass verified mappings or mode selection.
"""
import json
from datetime import datetime, timezone
from homeassistant.components.todo import TodoListEntity, TodoItem, TodoItemStatus, TodoListEntityFeature
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from .entity import DobbyEntity

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([DobbyTodo(entry.runtime_data)])

class DobbyTodo(DobbyEntity, TodoListEntity):
    _attr_icon = "mdi:format-list-checks"
    _attr_supported_features = (TodoListEntityFeature.CREATE_TODO_ITEM |
                                TodoListEntityFeature.DELETE_TODO_ITEM |
                                TodoListEntityFeature.UPDATE_TODO_ITEM |
                                TodoListEntityFeature.MOVE_TODO_ITEM |
                                TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM)
    def __init__(self, c):
        super().__init__(c, "queue", "Today's rooms", "todo")

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.controller.queue_entity_id = self.entity_id

    @callback
    def _changed(self):
        self.async_write_ha_state()
        self.async_update_listeners()

    @property
    def todo_items(self):
        items = []
        for j in self.controller.engine.jobs:
            r = self.controller.rooms.get(j["area_id"], {})
            a = self.controller.engine.active
            a = a if a and a["uid"] == j["uid"] else {}
            description = json.dumps({"area_id": j["area_id"], "mode": r.get("mode"),
                                      "map": r.get("map_name"), "segments": r.get("segments", []),
                                      "default_priority": r.get("priority", 100), "source": j.get("source"),
                                      "reason": j.get("reason", ""), "note": j.get("note", ""),
                                      "immediate_request": self.controller.engine.is_immediate(j["uid"]),
                                      "requested_mode": a.get("requested_mode", j.get("requested_mode", r.get("mode"))),
                                      "effective_mode": a.get("mode", j.get("executed_mode", r.get("mode"))),
                                      "executed_mode": j.get("executed_mode"),
                                      "mopping_skipped": j.get("mopping_skipped", False),
                                      "result": j.get("result", ""),
                                      "fallback_reason": a.get("fallback_reason", j.get("fallback_reason", ""))}, indent=2)
            args = {"summary": r.get("name", j["area_id"]), "uid": j["uid"],
                    "status": TodoItemStatus.COMPLETED if j["status"] == "completed" else TodoItemStatus.NEEDS_ACTION,
                    "description": description}
            if "completed" in getattr(TodoItem, "__dataclass_fields__", {}):
                args["completed"] = datetime.fromtimestamp(j["completed_at"], timezone.utc) if j.get("completed_at") else None
            items.append(TodoItem(**args))
        return items

    async def _command(self, action, data):
        try:
            return await self.controller.command(action, data)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err

    async def async_create_todo_item(self, item):
        name = str(item.summary or "").casefold()
        matches = [r for r in self.controller.rooms.values() if r["cleanable"] and name in (r["area_id"].casefold(), r["name"].casefold())]
        if len(matches) != 1:
            raise HomeAssistantError("Use the exact name of one cleanable Area, or add it through the Dobby card")
        await self._command("enqueue", {"area_id": matches[0]["area_id"]})

    async def async_update_todo_item(self, item):
        job = self.controller.engine.find(item.uid)
        if not job:
            raise HomeAssistantError("Queue item no longer exists")
        room_name = self.controller.rooms.get(job["area_id"], {}).get("name", job["area_id"])
        if item.summary is not None and item.summary != room_name:
            raise HomeAssistantError("Room names come from Home Assistant Areas. Rename the Area instead.")
        if item.status == TodoItemStatus.COMPLETED and job["status"] != "completed":
            await self._command("complete", {"uid": item.uid})
        elif item.status == TodoItemStatus.NEEDS_ACTION and job["status"] == "completed":
            await self._command("enqueue", {"area_id": job["area_id"]})
        if item.description is not None:
            try:
                note = json.loads(item.description).get("note", "")
            except (ValueError, AttributeError):
                note = item.description
            await self._command("update_note", {"uid": item.uid, "note": note})

    async def async_delete_todo_items(self, uids):
        if self.controller.engine.active and self.controller.engine.active["uid"] in uids:
            raise HomeAssistantError("Dock/pause Dobby before deleting the current room")
        for uid in uids:
            await self._command("remove", {"uid": uid})

    async def async_move_todo_item(self, uid, previous_uid=None):
        await self._command("move", {"uid": uid, "previous_uid": previous_uid})

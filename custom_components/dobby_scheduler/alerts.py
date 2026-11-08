"""Tell a person when Dobby needs them; stay quiet while it heals itself.

Two channels, both optional and both best-effort (a failed notification never
affects the scheduler):

* A Home Assistant Repairs issue while a fault needs attention. It is removed
  automatically when the fault clears, whoever clears it.
* A message to a configured notify action (for example
  ``notify.mobile_app_phone``). Phone notifications carry a Retry button that
  calls the same conservative retry as the card.
"""
from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)
ISSUE_ID = "needs_attention"
RETRY_ACTION = "DOBBY_SCHEDULER_RETRY"


def _issue_registry():
    try:
        from homeassistant.helpers import issue_registry as ir
    except ImportError:  # Test stubs without the full helper package.
        return None
    return ir


class Alerts:
    def __init__(self, hass, domain, title):
        self.hass, self.domain, self.title = hass, domain, title
        self.sent = []  # Recent deliveries, for diagnostics and tests.

    def issue_id(self, entry_id):
        return f"{ISSUE_ID}_{entry_id}"

    def raise_issue(self, entry_id, fault):
        ir = _issue_registry()
        if ir is None:
            return
        ir.async_create_issue(
            self.hass, self.domain, self.issue_id(entry_id),
            is_fixable=False, is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_ID,
            translation_placeholders={"name": self.title, "fault": fault[:300]},
        )

    def clear_issue(self, entry_id):
        ir = _issue_registry()
        if ir is not None:
            ir.async_delete_issue(self.hass, self.domain, self.issue_id(entry_id))

    async def notify(self, service, title, message, retry=False):
        self.sent.append({"service": service, "title": title, "message": message, "retry": retry})
        self.sent = self.sent[-20:]
        if not service:
            return
        domain, _, name = service.partition(".")
        if domain != "notify" or not name:
            _LOGGER.warning("Dobby notify target must be a notify action, not %s", service)
            return
        data = {"title": title, "message": message}
        if retry and name.startswith("mobile_app_"):
            data["data"] = {"tag": "dobby_scheduler",
                            "actions": [{"action": RETRY_ACTION, "title": "Retry"}]}
        elif name.startswith("mobile_app_"):
            data["data"] = {"tag": "dobby_scheduler"}
        try:
            await self.hass.services.async_call("notify", name, data, blocking=False)
        except Exception as err:  # Never let a notification failure stop cleaning.
            _LOGGER.warning("Dobby notification via %s failed: %s", service, err)

    async def handle(self, events, entry_id, service):
        for ev in events:
            kind = ev.get("kind")
            if kind == "attention":
                self.raise_issue(entry_id, ev.get("fault", ""))
                await self.notify(service, f"{self.title} needs you",
                                  f"{ev.get('fault', 'Unknown fault')}. Dobby could not clear this "
                                  "by itself. Check the robot and dock, then press Retry.", retry=True)
            elif kind == "resolved":
                self.clear_issue(entry_id)
                await self.notify(service, f"{self.title} is back on track",
                                  "The fault has cleared and the queue will continue.")
            elif kind == "skipped":
                await self.notify(service, f"{self.title} skipped {ev.get('room', 'a room')}",
                                  f"{ev.get('room', 'A room')} kept failing ({ev.get('reason', '')}), "
                                  "so it is skipped for today. It will be queued again tomorrow.")

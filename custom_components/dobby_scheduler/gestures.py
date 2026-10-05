"""Pure gesture recognition for labelled inputs, with no robot side effects.

Raw integration event buses are deliberately not guessed. An event entity or an
input_button bridge gives a persistent, label-able Home Assistant identity.
"""
from __future__ import annotations
from datetime import datetime, timezone

GESTURE_LABELS = ("dobby_room_toggle", "dobby_room_double_toggle", "dobby_room_press")
PRESS_ALIASES = ("room_press",)
STATE_DOMAINS = {"switch", "light", "binary_sensor", "input_boolean"}
PRESS_DOMAINS = STATE_DOMAINS | {"button", "input_button", "event"}
SHORT_PRESS_TYPES = {
    "press", "pressed", "single", "single_press", "single_click", "click",
    "short_press", "short_release", "single_short_release", "press_end",
    "button_single", "key_pressed", "ring",
}


def resolve_gesture(labels):
    """Return one mode; conflicting labels fail closed, never choose the shortest."""
    found = set(labels) & set(GESTURE_LABELS)
    if set(labels) & set(PRESS_ALIASES):
        found.add("dobby_room_press")
    if len(found) > 1:
        return None, "Conflicting gesture labels; choose exactly one"
    return (next(iter(found)), "") if found else (None, "")


def timestamp(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.timestamp()
    except (ValueError, TypeError, OverflowError):
        return None


class PressDetector:
    """Single rising edge, or a fresh button/event timestamp. One ACK per cooldown."""
    def __init__(self):
        self.cooldowns = {}

    def feed(self, entity, old, new, attributes, now, wall_now, started_at,
             cooldown=5.0, automation=False, reject_automation=True,
             event_type=""):
        domain = entity.split(".", 1)[0]
        if domain not in PRESS_DOMAINS or old is None or new in (None, "unknown", "unavailable", ""):
            return False
        if old == new or old == "unavailable":
            return False
        # An input_button is an explicit bridge for raw ZHA/Shelly/etc events.
        # Such a bridge is intentionally pressed by an automation.
        if automation and reject_automation and domain != "input_button":
            return False
        if domain in STATE_DOMAINS:
            accepted = old == "off" and new == "on"
        else:
            at = timestamp(new)
            previous = timestamp(old)
            accepted = (at is not None and at >= started_at and
                        0 <= wall_now - at <= 10 and
                        (previous is None or at > previous))
            if domain == "event":
                emitted = str(attributes.get("event_type", ""))
                accepted = accepted and (emitted == event_type if event_type else emitted in SHORT_PRESS_TYPES)
        if not accepted or now < self.cooldowns.get(entity, 0):
            return False
        self.cooldowns[entity] = now + cooldown
        return True

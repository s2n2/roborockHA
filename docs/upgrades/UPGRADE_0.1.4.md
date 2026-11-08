# Dobby Scheduler 0.1.4 - button and switch gestures

## What changed

| Entity label | Trigger |
|---|---|
| `dobby_room_toggle` | One complete switch cycle: OFF -> ON -> OFF, or ON -> OFF -> ON. Two real transitions within the configured window (default 2 seconds). |
| `dobby_room_double_toggle` | Two complete switch cycles: OFF -> ON -> OFF -> ON -> OFF, or the opposite. Four transitions within the window. |
| `dobby_room_press` | A single momentary press, fresh button timestamp, or supported short-press event. |

The short spelling `room_press` is also recognised as an alias for
`dobby_room_press`. The setup UI creates and uses the prefixed label.

**Behaviour change:** through 0.1.3, `dobby_room_toggle` meant FOUR changes.
It now means TWO, as requested. To retain the old gesture on an existing input,
replace its label with `dobby_room_double_toggle`. The update does not silently
rewrite your labels. Pause automatic scheduling while you review this.

Only one gesture type is allowed per input. Conflicts block the input and are
shown in the setup pane rather than letting a shorter gesture win.

## Configure without YAML

Open the card gear -> Buttons & switches.

1. Click Create missing Dobby labels (the existing room labels are preserved).
2. Choose Single press, One switch cycle, or Two switch cycles.
3. Select the input entity. Its Home Assistant Area determines the room; an
   entity Area takes precedence over the device Area. That Area must be labelled
   `dobby_cleanable`; its map/mode still needs normal verification before cleaning.
4. For an `event.*` entity, optionally select its exact short-press event type.
   Leaving this blank recognises common names. A datalist shows the selected
   entity's advertised event types; no platform-specific YAML list is needed.
5. Save gesture label. This replaces other Dobby gesture labels on that entity
   and preserves unrelated labels. Edit/remove controls are in the same pane.

Changing a room's labels or replacing a switch does not require code edits.
Do not label both a physical input and its mirrored light output.

## Single-press sources

- Momentary `binary_sensor`, `switch`, `light`, or `input_boolean`: only OFF -> ON
  counts. The ON -> OFF release never queues another room. An ordinary latching
  toggle used with this label consequently triggers only on its on-direction;
  use a proper button/event entity for a button that reports presses differently.
- `button.*` and `input_button.*`: a new, fresh last-pressed timestamp counts.
  A button entity generally reflects a HA/UI/service action, not necessarily a
  hardware button signal. Never select a restart/reset button just to get a
  press event; its ordinary device action still occurs.
- `event.*`: a new, fresh timestamp plus a recognised short-press type. Automatic
  names include single, single_press, single_click, press, pressed, click,
  short_press, short_release, single_short_release, press_end, button_single,
  key_pressed, and ring. Long/double/hold/repeat types are excluded by default.
  A vendor-specific exact event type can be set in the UI.

A `press` event emitted on button-down is accepted immediately; this cannot
predict whether the user will subsequently hold the button. Choose a completed
short-release type where the device provides one to distinguish holds fully.

Old timestamps restored at startup, attribute-only changes, unknown values and
unavailable recovery are ignored. Button/event timestamps must be timezone-aware,
newer than integration startup and no more than 10 seconds old. The first state
creation is ignored; the first subsequent fresh press can be accepted even if
the previous state was unknown. Slow cloud reporting may therefore be unsuitable.

A button that ONLY emits raw `zha_event`, `shelly.click`, or another event-bus
message needs a small ordinary HA UI automation that presses an `input_button`
helper. Give that helper the correct Area and `dobby_room_press` label. Raw bus
messages themselves have no entity labels. Deliberate input_button bridge presses
are accepted even when Ignore automation-generated changes is enabled; other
known automation-generated input changes retain that filter.

## Queue and Locate feedback

All three gesture types share the same accepted-request path:

- Add/promote this room to next, without duplicates or interrupting an active room.
- Save the queue, then request `vacuum.locate` on the configured vacuum.
- A room that was already completed becomes pending again.
- A request for the room already being cleaned does not create an extra pass or
  issue a success acknowledgement, since no new request was queued.

Locate feedback defaults ON. The existing explicit acknowledgement setting is
preserved: check that Robot & schedule -> Locate voice acknowledgement is enabled.
The Buttons & switches pane shows its current setting and a Test Locate button.
This uses the robot's normal locate sound (for Dobby, the usual locator phrase),
not generated speech. Robot volume/DND/firmware may suppress it; the integration
does not disable DND. A failed/timeout Locate is logged and never removes a saved
room. Invalid/unlabelled rooms and requests that fail storage are not acknowledged.
The default 5-second per-input cooldown prevents repeat queues/announcements.

## Install through your repository/HACS

Back up HA and pause automatic scheduling. Upload the archive CONTENTS to the
root of `s2n2/roborockHA`, preserving any unrelated edits made since the supplied
0.1.3 release. Publish a new `v0.1.4` release/tag. In HACS refresh the repository
information and install/redownload that release. Fully restart Home Assistant,
then refresh the browser/app. Do not delete the integration, helpers or queue.
No new resource entry is needed. Existing card YAML remains:

```yaml
type: custom:dobby-scheduler-card
title: Dobby
```

Automatic scheduling settings, map verification, room modes, dock/empty logic,
the responsive 0.1.3 layout and the 0.1.2 registration fix are retained.
New per-input event filters live in the existing scheduler storage, not YAML.

## Validation and limits

- 165 passing Python tests (including 58 new gesture/acknowledgement tests).
- 21 existing browser UI checks and 20 new gesture-pane checks.
- 5 browser startup/registry tests and 11 Node registration regressions.
- Python compilation, JavaScript syntax and offline repository metadata checks.

These use simulated HA states/backends and headless Chromium, not the user's
live Home Assistant or robot. No GitHub upload, HACS installation or physical
cleaning/Locate was performed. The supplied 0.1.3 archive is the patch baseline.
Test one labelled input per mode while automatic scheduling is OFF. Check that
one press/cycle queues the correct room and produces just one Locate command,
then test its release, repeats, relabelling and a second independent input.

## Primary API references

- https://www.home-assistant.io/integrations/event/
- https://www.home-assistant.io/integrations/button/
- https://www.home-assistant.io/actions/input_button.press/
- https://www.home-assistant.io/actions/vacuum.locate/
- https://www.hacs.xyz/docs/publish/integration/

# Dobby Scheduler 0.1.5 - activity and confirmed room

## Two new reusable sensors

- `sensor.dobby_scheduler_activity`: what the robot reports now, e.g. Cleaning
  Kitchen, Vacuuming and mopping Kitchen, Mopping Bathroom, Returning to dock,
  Emptying dustbin, Washing mop, Drying mop, Charging, Docked, Paused, or Main
  brush jammed. The state is a string, not a numerical measurement.
- `sensor.dobby_scheduler_room_stable`: last room name whose source reading stayed
  unchanged for the full confirmation window. The default window is 60 seconds.

The existing `sensor.dobby_scheduler_status` is unchanged: that is the state of
THE SCHEDULER (disabled/waiting/cleaning/attention, etc.), not necessarily the
physical robot. Activity also reports cleaning started outside this scheduler.
This does not grant the scheduler ownership of an app-started job.

Each sensor has a unique ID and can be reused in cards, templates, automations,
and announcements. Typical IDs above assume there was no naming collision or
manual entity rename. Diagnostics -> activity data and the frontend's entity
list contain the IDs actually registered on your installation.

## How the one-minute room filter works

Only the ROOM NAME is delayed. Native returning, pause, error and dock states
are presented when Home Assistant reports them, without an additional minute.
This does not accelerate or poll the robot's integration more often.

- A new cleaning spell initially says Cleaning (or the appropriate mop mode).
  Its room name is included after the room reading remains unchanged for a full
  confirmation window DURING that cleaning spell.
- Shorter room readings are never published as new room names. During transit,
  the activity retains the last confirmed room in the current cleaning spell.
  `room_is_current: false` distinguishes that retained room from the latest raw
  location. The confirmed-room sensor has `matches_current_reading` too.
- The confirmed-room sensor is intentionally a filtered/last-confirmed location,
  not an instantaneous map dot. It may also confirm a room while idle/docked if
  the underlying room sensor continues to report it there.
- Return to dock, pause, error or loss of the vacuum clears the ACTIVITY room
  latch, so a new run cannot instantly inherit its previous job's location.
- Unknown/unavailable room readings reset their confirmation and do not become
  room names. Activity can still say Cleaning when the room sensor is missing.
  The standalone room sensor becomes unavailable if its source is unusable.
- Map, source, robot or confirmation-interval changes begin a fresh window.
  Restart/reload starts a fresh window too; a previous timer is not restored.
- Confirmation happens at the first local update at/after 60 seconds, normally
  within the following five-second refresh. Attribute-only source changes do
  not reset the timer. Source state events reset it immediately.
- Entries are recorded at confirmation time, not backdated to first arrival.
  This is not a retrospective filter for existing raw room history.

The queue target is not used as an observed room: a command to clean Kitchen
is not proof that the robot has reached Kitchen. It remains available separately
as the Activity sensor's `scheduled_room` attribute.

## Source settings - no new YAML or per-room wiring

Open the card's gear -> Robot & schedule -> Activity & room history.

- Current-room sensor: for this installation, `sensor.dobby_current_room`.
- Optional detailed robot-status sensor.
- Optional dock-error sensor.
- Optional mop-drying binary sensor.
- Room confirmation seconds: default 60, configurable from 1 to 600.

Blank optional fields look for conventional names matching the selected vacuum,
for example `sensor.<vacuum_name>_current_room`. They do not pick an arbitrary
sensor from a different robot. An explicit selection remains authoritative even
if unavailable; it is never silently replaced by another source.

Find controls for this vacuum suggests these fields where the usual entities
exist. Save only after reviewing the suggestions. Existing vacuum, error, mode,
washing, emptying and water-problem selections are reused. The raw detailed
status is optional; no new internal Roborock API dependency was added.

Named room readings work directly. A numerical room reading is translated using
the fetched maps and explicitly identified current map; an unknown map or unknown
segment is not guessed. If the source entity has been renamed, select it here.
Never choose a Dobby Scheduler output as an input; those self-references are rejected.

The card now displays a Robot activity row separately from scheduler status.
Tap it to open the Activity sensor's normal Home Assistant more-info dialog.

## Replace the noisy logbook card

The native Activity/logbook card supports filtering states, not filtering each
entry by how long it later lasted. Use the new sensor instead of the raw room
and whole-device targets. See `dashboard-activity-card.yaml`:

```yaml
type: logbook
title: Dobby activity
target:
  entity_id:
    - sensor.dobby_scheduler_activity
hours_to_show: 24
name_detail: entity
```

For just confirmed-room changes, use `dashboard-confirmed-rooms-card.yaml`:

```yaml
type: logbook
title: Dobby confirmed rooms
target:
  entity_id:
    - sensor.dobby_scheduler_room_stable
hours_to_show: 24
name_detail: entity
```

Remove the original `device_id` target and `sensor.dobby_current_room` from those
cards. Otherwise their original, unfiltered events remain included. Both the
original room entity and the original vacuum entity remain untouched elsewhere.
If using a state_filter field, use `[]`, not HTML-escaped square brackets.

Leave these text sensors in Recorder/Activity if you want their history. History
begins when the new entities are installed. There is no separate logbook.log
call, so the package does not deliberately create duplicate custom log entries.

Examples elsewhere:

```jinja
{{ states('sensor.dobby_scheduler_activity') }}
```

```yaml
condition: state
entity_id: sensor.dobby_scheduler_activity
attribute: activity_code
state: returning
```

## Installation / HACS

1. Back up Home Assistant and keep automatic cleaning off while updating.
2. Upload the CONTENTS of the complete ZIP to `s2n2/roborockHA`, or merge the
   runtime patch over version 0.1.4. Preserve any unrelated edits of your own.
3. Publish a new release/tag `v0.1.5`. Install/redownload that version in HACS.
4. Fully restart Home Assistant, then refresh the browser/app. Do not delete or
   recreate the integration, queue, labels, room mappings or existing helpers.
5. Review the Activity & room history section, then replace the logbook card.

No new manual JavaScript resource is needed. Existing Dobby card YAML stays:

```yaml
type: custom:dobby-scheduler-card
title: Dobby
```

## Scope and validation

This is a read-only reporting extension. The Engine class, robot commands,
completion/emptying rules and gesture/Locate implementation are unchanged.
The settings dictionary gains only reporting options. Observation state is held
in memory, not written every five seconds to the persistent queue store.

Based on the supplied v0.1.4 archive. The live GitHub repository could not be
retrieved during this build. Nothing was uploaded to GitHub, installed through
HACS or run against a physical robot.

- 245 Python simulation tests passed, including 80 new reporting/adapter tests.
- 21 new browser checks cover activity, source settings, more-info, diagnostics,
  escaped values and narrow layout.
- 46 existing browser checks (21 general UI, 20 gestures, 5 startup) passed.
- 11 Node registration regressions passed.
- Python compilation, JavaScript syntax, manifest/repository checks and YAML
  parsing passed locally.

These are local simulations, not Home Assistant integration-test fixtures,
hassfest certification, or a hardware acceptance test. Known/unknown status is
only as accurate and current as the underlying integration's reports.

Official references checked for this change:
- https://www.home-assistant.io/dashboards/logbook/
- https://developers.home-assistant.io/docs/core/entity/sensor/
- https://www.home-assistant.io/integrations/roborock/
- https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/roborock/vacuum.py

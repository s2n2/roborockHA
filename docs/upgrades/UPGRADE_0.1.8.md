# Dobby Scheduler 0.1.8 - shorter Activity text with the room

## What changes

The existing `sensor.dobby_scheduler_activity` now uses shorter state strings:

| Reported activity | New example |
|---|---|
| Vacuum and mop | `Vac + mop · Kitchen` |
| Vacuum only | `Vacuuming · Hallway` |
| Mop only | `Mopping · Bathroom` |
| Custom/unknown cleaning mode | `Cleaning · Kitchen` |
| Returning to the dock | `Returning` |
| Dock dust collection | `Emptying` |
| Fault | `Main brush jammed` (fault details are not abbreviated) |

The existing card and logbook already read this sensor, so their YAML stays the
same. This is a reporting update, not a new entity or a change to the queue.

## Room confirmation versus the scheduled target

The old code omitted the room until a reported room remained unchanged for 60
seconds. A missing/unresolvable current-room sensor also left the activity with
no room indefinitely. The screenshot alone does not distinguish these causes.

- A dot (`Vac + mop · Kitchen`) shows the confirmed observed room. The existing
  configurable one-minute filter remains. During a short transit it can still
  be the last confirmed room; `room_is_current` distinguishes that case.
- An arrow (`Vac + mop → Kitchen`) shows THIS scheduler's active dispatched
  job target while no observed room has confirmed. It is a job/destination label,
  not a claim that the vacuum is physically in Kitchen. It does not wait a minute.
- A preparing, cancelled, interrupted, faulted or merely next-in-queue room is
  never used as the target fallback. There must also be actual cleaning telemetry.
- App-started cleaning with no owned job still needs a confirmed room reading;
  the scheduler cannot infer that room from a pending daily queue.
- Return, pause, errors and dock operations take precedence and do not acquire
  a misleading cleaning-room suffix.

No source or room-number list needs to be changed. For independent app-started
runs, check Gear -> Robot & schedule -> Activity & room history -> Current-room
sensor. For Dobby this is normally `sensor.dobby_current_room`. Source auto-
detection remains unchanged. Numerical room readings still require a matching
fetched map. The standalone Confirmed room sensor is never fed a job target.

## Reusable attributes

Activity adds:

```yaml
display_room: Kitchen
display_room_source: confirmed  # or scheduled; null if no displayed room
detail: Vacuuming and mopping Kitchen
```

Existing `confirmed_room`, `room_is_current`, `scheduled_room`, `activity_code`
and water-fallback attributes are retained. `activity_code` values do not change.
Existing automations matching literal Activity state strings must use the new
strings, or preferably the unchanged `activity_code` attribute. Internal
`sensor.dobby_scheduler_status` phase names are unchanged.

## Installation

1. Upload the full ZIP contents to `s2n2/roborockHA`, or merge the patch over the
   supplied 0.1.7 source. Preserve any independent edits.
2. Publish a new `v0.1.8` release and install/redownload it in HACS.
3. Fully restart Home Assistant, then refresh the browser. Keep the same entry,
   helpers, room labels, mappings, to-do queue and card. No resource to add.
4. As before, restart clears runtime-only immediate-request permissions. Repeat
   the switch gesture for any priority room you want authorised to run now.

The complete 0.1.7 scheduling engine, commands, gesture detection, water-tank
fallback and job-completion rules are unchanged. This release does not resolve
an unrelated missing sensor, change integration polling, or backfill history.

## Scope and verification

Baseline: supplied `roborockHA_v0.1.7.zip`. The public GitHub fetch was unsuccessful;
independent edits in the live repository were not inspected or overwritten.
Nothing was pushed to GitHub, installed in HA, or sent to your robot.

Completed locally:
- 424 Python simulations (389 existing cases plus 35 new compact/target cases).
- 23 Chromium Activity/settings checks, including room labels, errors, narrow
  layout, escaped strings and no robot commands caused by presentation.
- 11 Node frontend registration regressions.
- Python compilation, JavaScript syntax and offline repository metadata checks.
- Byte comparisons confirm the scheduling engine and gesture implementation are
  unchanged relative to the supplied 0.1.7 archive.

These are simulated Home Assistant services/registries and browser data, not a
live Home Assistant installation, HACS/hassfest run or physical robot test.

Official references checked:
- https://www.home-assistant.io/integrations/roborock/
- https://www.hacs.xyz/docs/publish/integration/

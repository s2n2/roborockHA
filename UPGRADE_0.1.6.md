# Dobby Scheduler 0.1.6 - vacuum-only fallback for water-tank alerts

## What changes

The new **Vacuum instead when a water tank needs attention** option is ON by
default, including when upgrading from 0.1.5. Find it under the card's gear ->
Robot & schedule, below Water problem entities. It can be switched off there;
no YAML, room labels or room-number mappings need to change.

For a room labelled Vacuum + mop OR Mop only, a confirmed alert from the
configured water-tank problem sensors selects **vacuum** for this attempt.
Dobby's vacuum mode must be reported/confirmed before the room-clean command
is sent. The scheduler does not request mop water flow for that dry attempt.

This applies to the existing configured tank-problem inputs: clean-water tank
empty/not fitted, onboard water shortage, and dirty-water tank full/not fitted.
Some Roborock entities combine more than one tank condition. An `on` reading is
therefore described as "water tank needs attention", not proof of exactly which
condition occurred. Only put those mop/tank limitations in Water problem entities;
do not put brush errors, overheating or other robot faults in that list.

All configured water inputs must have a known on/off reading to choose a new
fallback from a tank alert. An unavailable/unknown sensor is not taken to mean
an empty tank. Existing vacuum-only rooms do not need water telemetry.

## Current error shown in the screenshot

The old saved **Water system needs attention** fault is deliberately not silently
cleared by an update. After installing 0.1.6 and with Dobby docked, press **Retry
after checking** once. If this was a manual cleaning session, press **Run now**
again. Otherwise the normal enabled/away/window rules control when it runs.
You do not have to refill the tank to use the vacuum-only fallback.

If it still waits, check Diagnostics:

- `water_problem`: true means at least one configured tank input reports on.
- `water_status_known`: true means all configured tank inputs report on or off.
- `water_problem_sources`: entity IDs currently reporting a tank alert.
- `water_unavailable_sources`: entity IDs that need their connection/config checked.

General robot errors, unsupported modes, unavailable robot/error telemetry,
incorrect maps, low battery, an occupied house (without a supervised override),
closed cleaning window and explicit pause helpers still block. This update does
not clear robot errors, disable DND or claim it can overrule firmware refusing a
vacuum-only command.

## Changes during a job

- Before the room command is sent: switch to vacuum and wait for confirmation.
- During a wet attempt with no successful completion proof: explicitly cancel/dock,
  wait for a settled dock with its required service sensors clear, then restart
  that room from the beginning in vacuum-only mode. A stale `docked` reading
  after the original command is not enough to launch a replacement command.
- The dry retry retains its mode even if a tank signal clears during redocking;
  it cannot repeatedly bounce between wet and dry attempts. Requeueing the room
  or the next daily reset removes that temporary retry preference.
- A fresh successful wet-clean record received just as the tank empties is not
  discarded: finish that successful job's normal dock/empty process instead.
- Arrival, pause, connection problems and failed commands retain their normal
  interruption/attention handling. No failed service is treated as success.

A running dry attempt is not changed back to wet mode halfway through when water
is restored. Subsequent ordinary pending jobs read the current water state and
use their original labels again when clear.

## Completion is honest

Automatic completion still requires the observed clean, fresh successful robot
record, docking, and required dust emptying. Mop-only jobs downgraded to vacuum
now use the vacuum dust-empty rule, even when "Also empty after mop-only rooms"
is disabled.

The daily queue counts a successful dry fallback as done, but explicitly labels
it **Vacuumed only - mop skipped**. Job details and the native to-do description
retain `requested_mode`, `executed_mode`, `mopping_skipped`, `fallback_reason`
and `result`. An explicit manual confirmation is marked manual, not robot proof.

Refilling the tank does not silently repeat already completed rooms. Tap one to
repeat it if desired; the next daily reset otherwise restores the usual list and
mop labels.

## Reusable reporting

The existing Status and Activity sensors now also expose the active job's:

```yaml
requested_mode: vac_and_mop
effective_mode: vacuum
water_fallback: true
fallback_reason: Water tank needs attention; mopping skipped
```

Status also has `mopping_skipped_rooms`, listing today's completed dry fallbacks.
Activity's state remains based on physical robot telemetry; the queue's planned
room is still not treated as its observed current location. The one-minute room
filter, gestures and Locate acknowledgement remain in place.

## Install

1. Back up Home Assistant; keep automated cleaning paused during the update.
2. Upload the extracted full archive to the root of `s2n2/roborockHA`, or merge
   the patch over the supplied **0.1.5** repository. Preserve independent edits.
   The patch includes current-version test updates so repository checks remain
   consistent, not just the runtime files.
3. Publish a NEW release/tag **v0.1.6**. Install/redownload that version in HACS.
4. Fully restart Home Assistant and refresh the browser/app. Do not delete the
   existing integration, helpers, queue, labels, mappings or dashboard card.
5. Check the new option is on. Clear the existing water fault with Retry as
   described above, and supervise one room before unattended use.

The integration domain and storage version are unchanged. There is no new
manual dashboard resource. HACS/hassfest checks still run in your repository;
they were not run against a live HA installation here.

## Validation and scope

Based on the supplied `roborockHA_v0.1.5.zip`. The live GitHub repository could
not be retrieved, so any independent changes there must be merged by you.
Nothing was installed in Home Assistant or pushed to GitHub by this build.

Local checks passed:

- 322 Python tests (245 existing, plus 77 new water-fallback/adapter cases).
- 88 browser checks: general card (21), activity (21), gestures (20), startup (5),
  and new fallback card/settings tests (21).
- 102 responsive layout assertions and 11 Node registration checks.
- Python compilation, JavaScript syntax and offline repository validation.

The layout suite's stale two-section expectation from before 0.1.5 was updated
to the existing three sections: robot, schedule and activity. The tests use
simulated HA registries/backends/telemetry, not physical robot hardware or a
running Home Assistant installation. They are not a guarantee of all firmware
behaviour. See `docs/validation-0.1.6.txt` and the test output files.

## Primary documentation checked

- https://www.home-assistant.io/integrations/roborock/ (tank entity meanings)
- https://www.hacs.xyz/docs/publish/integration/ (publishing/installing releases)

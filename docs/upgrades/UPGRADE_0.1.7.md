# Dobby Scheduler 0.1.7 - immediate switch-request batches, even while home

## Cause in the supplied 0.1.6 build

The gesture handler only enqueued/promoted a job and requested Locate. `urgent`
changed its position, but the runner still required automatic scheduling or a
manual session, absence permission, the away delay and the cleaning window.
A priority job was therefore not an immediate cleaning request.

## New behaviour (ON by default, including upgrades)

Gear -> Robot & schedule -> Schedule & gestures:

**Run switch/button requests immediately, even while home**

The same policy applies to all three existing labels:

- `dobby_room_press` (and its `room_press` alias): one press.
- `dobby_room_toggle`: one complete switch cycle.
- `dobby_room_double_toggle`: two complete switch cycles.

An accepted gesture saves/promotes the room and grants permission to run THAT
job without waiting for absence, the away delay, the automatic time window or
Automatic when away being enabled. Existing Locate feedback is retained.
Dispatch is kicked before waiting for the Locate response so a slow sound
command cannot itself impose a 45-second delay.

All gesture-requested rooms are processed one after another. The most recently
requested pending room is next, after the active job. Repeated requests do not
create duplicate queue items. You can still reorder within the requested tier.
Normal daily jobs cannot be moved ahead of authorised gesture jobs while that
batch exists. A running room is not pre-empted just to serve another request.

Example: while home, request Kitchen and let it start. Request Hallway and then
Bedroom. The sequence becomes Kitchen -> dock/empty -> Bedroom -> dock/empty ->
Hallway -> dock/empty. The ordinary daily Bathroom job remains pending. Once
the requested batch ends, ordinary automatic scheduling resumes ONLY if its
usual enabled, absence, delay and window checks allow it.

A generic dashboard Make next / urgent service request is still queue-only; it
is not equivalent to a physical gesture. Run now retains its existing explicit
whole-queue, at-home confirmation. The new handler never turns on that global
manual permission just to run switch-requested rooms.

## What remains enforced

Immediate means dispatch is requested now when the robot is ready, not that
hardware movement is instantaneous. Mode confirmation, current robot telemetry,
map verification, battery, error checks, configured extra pause/blocking helpers,
known home-presence state, competing-scheduler checks, a supported successful-clean
record and dock-service readiness are still required. A pending priority request
must wait if the robot is already doing an unrelated job or is not docked.
The card's status/Diagnostics gives the waiting reason.

A normal automatic job still docks on arrival. A fresh request for a DIFFERENT
room survives that normal arrival interruption and runs once docking finishes.
A gesture job is allowed to continue when somebody arrives; it was explicitly
requested for occupied-house use. Requests for the already active room still do
not queue a second pass or take over its permission policy.

Completion still requires cleaning proof, docking and the configured dust-empty
confirmation. A timeout is not success. Water-tank fallback from 0.1.6 is retained,
including safe redocking before a dry restart; the remaining immediate requests
survive that water-fallback redock. Unrelated errors are not ignored.

Robot DND/volume settings are not changed. They may suppress Locate or emptying;
this update does not force firmware to accept a command.

## Pause, restart and reset

Immediate permissions are deliberately runtime-only. Completed/removed rooms
lose their own grant. Pause & dock, explicitly turning automatic scheduling off,
reset, changing robots, disabling this new setting, and Home Assistant restart
or integration reload cancel outstanding immediate permissions. An actual safety
interruption (for example an unavailable presence input, a blocking helper or
robot error causing abort) cancels the immediate batch as well. The room items
remain pending unless the daily/reset operation replaces them.

After a restart or cancelled batch, repeat the appropriate button gesture for
EACH room you want to authorise now. Old persisted `urgent` flags or label/source
strings are NOT upgraded into occupied-house permission automatically. A command
fault still requires explicit Retry; neither a gesture nor this update silently
clears a saved fault.

A new deliberate gesture after Pause can request that room again even while the
Automatic when away switch remains off. For a persistent stop, use the existing
extra pause helper or turn the immediate-start setting off. Its OFF mode retains
the old queue-only behaviour and Locate acknowledgement.

Nightly reset still restores daily defaults and clears temporary priority. A reset
while a job is active remains deferred until it finishes/aborts; the next reset
then replaces that cleaning day's list as before.

## Card and reusable reporting

- The card shows **Switch-requested cleaning** with all authorised room names.
- Each job shows **switch request - run now** versus **priority (queue only)**.
- The settings and Buttons & switches pop-up explain the permission scope.
- `sensor.dobby_scheduler_status` exposes `immediate_requested_rooms`,
  `gesture_start_immediately`, and the active job's `start_policy`.
- Native to-do descriptions expose `immediate_request` for inspection, but editing
  that description is not a way to create permission.
- The API snapshot exposes `immediate_rooms` and a per-job `immediate_request`.
- Area assignments, modes, segments, labels, gesture detection, activity filtering
  and storage version are unchanged.

## Install through the existing GitHub / HACS repository

1. Back up Home Assistant. Upload the extracted full ZIP contents to the root of
   `s2n2/roborockHA`, preserving any independent changes. The patch ZIP applies to
   the supplied 0.1.6 archive and also includes changed tests/docs/workflow files.
2. Publish a NEW release/tag `v0.1.7`, then install/redownload that version in HACS.
3. Fully restart Home Assistant; refresh the browser/app. Do not delete/recreate
   the integration, queue, labels, mappings or helpers. No new resource is needed.
4. Confirm the new setting is on. Clear any pre-existing saved fault only after
   checking its cause, using Retry while docked.
5. Trigger a FRESH gesture after the restart. Merely being marked priority in the
   old saved queue does not retroactively grant permission to start while home.
6. Test two rooms while home under supervision. Check that each docks/empties,
   that the other daily rooms stay pending, and that Pause & dock cancels the batch.

## Scope / validation

Built against the supplied `roborockHA_v0.1.6.zip`. A public web fetch of the
repository was unsuccessful, so live repository differences are unverified.
Nothing was pushed to GitHub, installed in Home Assistant or sent to the robot.

Passed locally: **389 Python simulation tests** (322 existing + 67 new),
**106 browser checks** (88 existing + 18 new), **102 layout assertions**, and
**11 registration checks**. Python compilation, JavaScript syntax and the offline
repository metadata checker also passed. See docs/validation-0.1.7.txt.

Tests use simulated HA registries, services, telemetry and frontend data. They are
not actual HA integration-test fixtures, live hardware tests, HACS/hassfest
certification, or proof that a real robot supplied all required telemetry.

Official references checked:
- https://www.home-assistant.io/integrations/roborock/
- https://www.hacs.xyz/docs/publish/integration/

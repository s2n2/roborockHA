# Dobby Scheduler 0.1.9 – Dock command auto-check

## What this fixes

The previous scheduler latched service-call failures, including the Roborock
`dock: Error while calling APP_CHARGE` command, until **Retry after checking**
was pressed. The underlying command may have reached the robot even when the
Home Assistant call returns an error. This release doesn't assume success from
that exception; it checks the robot's subsequent observed state when cleaning is
next eligible.

## Behaviour

When scheduled cleaning becomes due, **Run now** is selected, or a recognised
switch/button gesture requests an immediate room:

1. Only `dock: ... APP_CHARGE ...` errors qualify. All other command and robot
   faults remain latched for manual attention.
2. Robot must be reported **docked continuously for the configured dock-settle
   interval** (10 seconds by default). It must be connected, have normal vacuum
   and optional dock-error sensors, and not be emptying or washing.
3. Normal scheduling permissions, configured hardware blockers, current map,
   battery, mode support, clean-record support, legacy automation and other
   preparation checks still apply. For scheduled runs, occupancy and away delay
   still apply; a gesture request keeps its existing at-home exemption.
4. If those checks pass, the saved command fault is cleared automatically.
   An unproved interrupted job stays **pending** and starts again from the
   beginning; a previously proved clean retains its completion evidence and
   follows ordinary dock/empty verification. Dock status by itself never counts
   as proof of a completed clean.
5. Only one automatic recovery is permitted **per queued job**, persisted across
   restarts. If a second APP_CHARGE command fails, check the dock and use manual
   Retry. Reset or a new deliberate room request begins a new attempt.

This does **not** issue a `vacuum.return_to_base` command just to probe the dock.
It is a read-only check. It cannot clear a real brush jam, an absent dust bag,
emptying failure or lack of a successful cleaning record.

## Installing from s2n2/roborockHA

Upload the full archive contents to the root of the GitHub repository, preserving
any independent changes. Alternatively apply the patch over the supplied 0.1.8
source. Publish a **new** `v0.1.9` GitHub release, then update the integration
through HACS. Fully restart Home Assistant and refresh the browser. Don't
recreate the integration or delete the queue, mappings, helpers or labels.

If Dobby is currently **charging and healthy**, wait until a room is eligible;
the card's error will be removed after dock verification, normally within the
configured dock-settle interval plus the scheduler's polling interval.

## Validation / limits

Simulation tests use fabricated telemetry; no commands were issued to a physical
robot or to the user's Home Assistant instance. If `APP_CHARGE` is still reported
while the vacuum is not actually docked, the scheduler deliberately leaves the
fault in place and needs inspection.

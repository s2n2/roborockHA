# Validation and first-run acceptance

Build: 0.1.0, 3 October 2026.

## Checks completed in the build environment

- **97 passing Python tests:** 64 deterministic scheduling tests and 33 Home Assistant-adapter contract simulations. Exact output is in `docs/python-test-output.txt`.
- **21 passing browser checks:** headless Chromium at desktop and 390-pixel mobile widths, with a mocked `hass.callWS` backend. Zero recorded browser JavaScript exceptions. Exact results are in `docs/frontend_test_results.json`.
- All integration Python files compiled successfully with Python 3.13.
- The frontend JavaScript passed `node --check`.
- All distributed YAML files loaded with both PyYAML and ruamel.yaml (duplicate-key rejection enabled for the latter).
- Manifest/translation JSON loaded; domain, bootstrap, version and frontend-resource references checked.

The initial attempt to run Playwright's bundled browser found that binary absent; the browser suite was then run successfully using the system Chromium executable. No test here connected to a real Home Assistant instance, used robot credentials, or moved hardware.

## What the simulations cover

Scheduling: default order, daily-only membership, urgent promotion, no duplicates, completed-room requeue, active-room priority protection, real list movement, safe initial disable, away delay, window/timezone boundaries, deferred overnight reset, restart recovery, no restored at-home override, low battery, errors, mode conflicts, wrong/unverified map, unavailable inputs, stale/failed/zero-area clean records, explicit clean/dock/empty confirmation, missed short auto-empty via counter, no proof from docking alone, no proof timeout during an active mop wash, empty failure and retry.

Gestures: four transitions, both starting states, debounce, cooldown, independent switches, slow sequences, attribute-only changes, unknown/unavailable, automation context filtering.

HA-adapter simulations: map response variants, invalid map data, preserved unrelated labels, duplicate/renamed/missing segments, entity Area overriding device Area, validated settings, vacuum change invalidation, unsupported success-record layouts, timestamp-only sensor rejection, read-only get-maps call, public segment service parameters, save before side effects, no unnecessary storage rewrite, and disabling only recognised old automation matches.

Browser: room selection, promote/reorder, settings popup, selected map numbers, confirmation invalidated after mapping edit, popup room selection, visible modal errors, unsaved fields surviving status polling, gesture-label requests, embedded instructions, diagnostics, no horizontal overflow at mobile width, and escaped HTML in Area names.

## What is NOT validated

This is **not** a live HA configuration check, Home Assistant integration-test fixture run, hassfest certification, HACS listing, hardware test, firmware guarantee, or proof of compatibility with every HA/Roborock version. The mocked HA modules validate adapter logic but cannot prove actual lifecycle, registries, entity platforms, device controls, permissions or persistence behave identically on your release. The real system must pass the acceptance steps below.

The completed-clean adapter reads internal cached Roborock coordinator data. If unsupported, starts or completion are blocked; that may require an adapter update after a Home Assistant upgrade. Simulated successful records do not prove your vacuum exposes these fields correctly.

## Supervised acceptance checklist

1. Make a HA backup. Install the integration and resource. Confirm the card loads and Automatic when away is OFF.
2. Select the real vacuum and controls. Confirm Diagnostics shows current battery, presence, no error, correct map, and a supported completed-clean record source. Do not substitute a last-clean timestamp to bypass a blocked record source.
3. Create labels. Fetch/check maps. Validate one small, known room against the robot's real map and save its verification. Confirm duplicate or wrong-map assignments visibly block.
4. Disable old Dobby and robot-app schedules. Select just that one room. Use Run now with the explicit at-home confirmation. Confirm the robot actually cleans the requested room in the requested mode.
5. Watch the returned success record: new begin/end for this run, success flag, zero error and positive area. Confirm it is not accepted during a mop wash or charging return.
6. Confirm actual docking, then a single dust-empty cycle (automatic or requested). Confirm the room is completed only after those checks and no second room starts early.
7. Test an interrupted room: make the presence signal change from away to home during a supervised run. Confirm return to dock, room remains pending, and it restarts only after another permitted absence. Do not use an at-home override for this particular test.
8. Restart HA during a supervised test. Confirm no item is falsely completed, the owned job recovers conservatively, and any at-home override is gone.
9. Label one local physical switch input. Test four real state changes within the window and confirm its Area becomes next, with no duplicates. Confirm normal single toggles and known automated lighting changes do not falsely request a room.
10. Test a configured water problem with a wet job and then a vacuum-only job. Inspect the different blocking behaviour. Do not send the robot onto unsuitable/wet/carpeted surfaces just to test labels.
11. Confirm emptying failure/DND produces a visible attention state instead of success or a rapid retry loop. Confirm a checked Retry can continue appropriately.
12. Set several daily Areas and default priorities, reorder today's queue, then invoke Daily defaults. Confirm the daily list/order returns. Check reset time and cleaning window in HA's local timezone.
13. Verify children/guest/babysitter presence and your motion-alarm policy. Only then enable unattended automatic scheduling.

Keep the robot within reach during first testing. If it acts unexpectedly, use its physical stop/pause control or the Roborock app, then disable the scheduler. Run only one controller at a time.

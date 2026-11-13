# Changelog

## 0.2.0 - No blocking errors

- No error needs acknowledging any more. The latched fault and the
  **Retry after checking** button are gone.
- Dobby-level problems (failed commands, missing clean record, timeouts, lost
  connection, internal errors) are logged, the robot docks, the room stays pending
  and the queue carries on after about two minutes. An internal error no longer
  switches the schedule off.
- A room that fails 3 times in a day is skipped (not blocked) until it is
  requested again or the next daily reset; other rooms keep running.
- A proved clean is kept when only dock/empty confirmation fails, instead of
  re-cleaning the room.
- Dobby only pauses for errors the Roborock itself reports (vacuum error or dock
  error sensor). The card mirrors that error and resumes as soon as it clears.
  An unavailable error sensor still waits at pre-flight but is not shown as a
  Roborock fault.
- Faults saved by older versions are dropped on upgrade. The 0.1.9 APP_CHARGE
  auto-recovery is superseded and removed.
- `dobby_scheduler.retry` is kept for compatibility; it now only clears the
  last-problem notice and gives skipped rooms another chance.
- New `last_issue` status attribute; `fault` now means a Roborock-reported error only.

## 0.1.9 - Safe automatic recovery from APP_CHARGE command faults

- The scheduler automatically reconciles an old `dock: Error while calling APP_CHARGE` when a scheduled, manual or gesture-requested cleaning attempt is eligible. Requires a continuously confirmed docked state, healthy available robot/dock sensors, idle dock services, and existing map/battery/queue safety checks.
- At most one automatic recovery per queued job (persistent across restart). Other errors and unsuccessful cleaning records remain blocked. Proven work is never marked complete without the existing dock/empty confirmation.
- A small note on the card explains the behaviour. No new settings, entities or dashboard resource.

## 0.1.8 - Compact room-aware Activity

- Shorter action labels and a confirmed-room separator in the existing sensor.
- Show a dispatched active-job target with an arrow while its location is
  unconfirmed; do not imply that a queued room is physical location.
- Keep 60-second observed-room filtering and fault/dock precedence.
- Reset the cleaning-room latch at new dispatched attempts, even if a short dock
  transition was missed; leave standalone location history independent.
- Retain activity_code values; add display_room, display_room_source and detail.
- Update in-card instructions and release metadata. Scheduling engine unchanged.
- 424 Python, 23 Chromium Activity/UI and 11 Node registration checks passed in
  simulations; no live Home Assistant or robot test.

## 0.1.7 - Immediate switch/button batches while home

- Separate per-job gesture-start permission from ordinary queue ordering.
- Process all freshly gesture-requested rooms while home, even with Automatic when
  away off, with no away-delay or automatic-window wait for those rooms.
- Preserve sequential cleaning, dock/empty verification and water fallback.
- Ordinary daily work and dashboard Make next do not acquire gesture permission.
- Keep fresh requests across an ordinary job's arrival-home interruption.
- Cancel runtime permissions on explicit pause, reset, restart or safety abort.
- Dispatch without waiting for Locate; rollback a gesture if queue storage fails.
- Show authorised rooms on the card, status attributes and native to-do metadata.
- 389 Python tests, 106 browser checks, 102 layout assertions and 11 registration
  checks passed locally with simulated data; not a live HA/hardware test.

## 0.1.6 - Vacuum-only fallback for tank alerts

- Default-on UI option: vacuum instead of mopping for confirmed configured tank alerts.
- Preserve room labels; keep unknown-source and general fault checks.
- Explicitly dock/cancel before restarting a wet attempt as dry; settle and confirm mode.
- Normal proof/dock/dust-empty rules remain required for automatic completion.
- Show requested versus effective mode; retain skipped-mopping results in daily history.
- Add fallback attributes to reusable sensors and native to-do descriptions.
- Saved older water faults still require one explicit Retry while docked.
- 322 Python tests, 88 browser checks, 102 layout assertions and 11 registration checks passed locally with simulated data.

## 0.1.5 - Reusable activity and confirmed rooms

- Added Activity and Confirmed room text sensors with unique IDs.
- Room names require a configurable full-minute confirmation by default;
  transient room readings do not enter the filtered history.
- Physical error/return/dock/mop state reporting is separate from scheduler state.
- Reset confirmation on source/map changes, unknown readings and restart; do not
  backdate new entries or treat the scheduled target as observed location.
- Added read-only optional sources and delay configuration to the card pop-up.
- Added a clickable Robot activity row and Activity diagnostics/instructions.
- Included native Activity/logbook card examples without raw/device targets.
- Preserved queue engine, gestures/Locate, completion rules and resource loading.
- 245 Python, 67 browser and 11 Node registration checks passed in simulations.


## 0.1.4

- Added three input gestures: single press, one switch cycle, two switch cycles.
- BREAKING label semantics: dobby_room_toggle is now two transitions; use
  dobby_room_double_toggle for the former four-transition behaviour.
- Added dobby_room_press, with room_press accepted as a short alias.
- Added button/input_button/event-entity support and UI event-type selection.
- Accepted requests share persistent queue-first Locate feedback, with error logs.
- Conflicting labels, restored timestamps, releases and duplicate requests are guarded.
- Added Buttons & switches setup UI, preserving responsive layout and startup fix.
- 165 Python, 46 browser and 11 Node registration checks passed in simulations.


## 0.1.3 - Responsive dashboard and setup

- Card-width container queries: narrow desktop columns receive the same careful
  layout as mobile cards, without relying only on browser viewport breakpoints.
- Full-width next-room summary on narrow cards; completion and battery below it.
- Consistent buttons, selected-room tiles, typography and empty states.
- Compact old-automation warning with an explicit Review action.
- No redundant empty execution section before rooms are configured.
- Accessible automatic-when-away switch and a quieter footer.
- Popup header/tabs stay visible while the form scrolls; room dropdown on small
  displays; settings divided into Robot & presence and Schedule & gestures.
- Automatic card height rather than a forced ten-row Sections layout.
- Preserve the 0.1.2 startup registration fix and all existing backend behaviour.
- Version/cache key bumped. No new Python dependencies, entities or migration.


## 0.1.2 - Wait for Home Assistant frontend registry

- Defer both the custom-card CLASS declaration and custom-element registration
  until Home Assistant has defined `home-assistant`, after its scoped registry
  polyfill is imported. Re-read the current registry after waiting.
- Publish picker metadata only after registration; retain duplicate-load guards.
- Add a versioned console message and `window.dobbySchedulerCardStatus` to make
  waiting, successful registration and failure distinguishable.
- Add 11 Node regression simulations and 5 Chromium startup checks, including
  reproducing the previous registration pattern's missing-element symptom.
- Keep backend scheduling, storage, helpers, map handling and queue logic unchanged.
- Tested with simulated registries/backends, not a live Home Assistant or robot.

## 0.1.1 - Integration visibility and bundled-card loading

- Classify Dobby as a service, not a helper.
- Load the bundled card via Home Assistant's frontend extra-module API.
- Keep resource registration and picker entries idempotent on repeated setup/import.
- Keep the same config entry, domain, entity identifiers and persistent queue.
- Add focused bootstrap/frontend regression checks.
- The robot engine and its safety/completion rules are unchanged.


## 0.1.0 - Initial experimental build

Label-driven room scheduling, persistent to-do queue, cleaning-mode selection,
verified room mappings, physical-switch gestures and the bundled configuration card.

Repository packaging includes hacs.json, brand icons, HACS/hassfest validation
workflows and simulated controller tests. Scheduling Python and frontend JavaScript
are unchanged from the original 0.1.0 bundle.

Not hardware-certified or validated in a live Home Assistant installation.
Review TESTING.md before enabling unattended operation.

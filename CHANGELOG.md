# Changelog

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

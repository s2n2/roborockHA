# Changelog

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

# Publishing s2n2/roborockHA - Dobby Scheduler 0.1.1

The manifest is already configured for `https://github.com/s2n2/roborockHA` and
code owner `@s2n2`. Upload the CONTENTS of this bundle to the repository root.
Keep `custom_components/dobby_scheduler/manifest.json` at that exact path.
Do not upload Home Assistant backups, credentials, config or .storage files.

## Validation and release

Run the GitHub validation workflow and review any errors. This local patch was
not run inside Home Assistant and has not been published to your repository.
After supervised checking, create a new GitHub release with tag `v0.1.1`.
Use a new tag; do not move the existing `v0.1.0` tag. For an experimental release,
mark it as a pre-release and enable pre-release updates for this repository in
HACS as needed. No ZIP release asset is required by this hacs.json.

## Install or update

Add `https://github.com/s2n2/roborockHA` as a HACS custom repository of type
Integration. Download/update Dobby Scheduler and restart Home Assistant fully.
For an existing installation, KEEP the current Dobby config entry and queue.
Do not delete helpers or create a second integration entry. For a new install,
add Dobby Scheduler in Settings > Devices & services after restarting.

Refresh the browser/app and add the Dobby Scheduler card from Add card > By card.
The module is automatically loaded by the integration in version 0.1.1.
Remove any old MANUAL Dobby resource entry, not the dashboard card itself.
The automatic resource URL is:

```text
/dobby_scheduler_frontend/dobby-scheduler-card.js?v=0.1.1
```

Manual card YAML still works:

```yaml
type: custom:dobby-scheduler-card
title: Dobby
```

## Changes in 0.1.1

- Integration type changed from helper to service for correct UI placement.
- Frontend dependency added; bundled module loaded using frontend.add_extra_js_url.
- Custom-card picker registration is idempotent, with a documentation link.
- Shared version constant keeps backend, entity and module URL consistent.
- No changes to room scheduling rules, stored config entry IDs, source robot
  entities, queue storage schema, room labels or map numbers.
- New setup and card-registration regression checks included.

The uploaded branch on GitHub was not retrievable in the build session. This
patch is based on the previously supplied `roborockHA_hacs_ready.zip` version
0.1.0. Compare any subsequent changes you made before replacing files.

## References

- https://developers.home-assistant.io/docs/creating_integration_manifest/
- https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/
- https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/frontend/__init__.py
- https://www.hacs.xyz/docs/publish/integration/

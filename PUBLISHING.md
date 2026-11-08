# Publishing s2n2/roborockHA (Dobby Scheduler)

The manifest points at `https://github.com/s2n2/roborockHA`, owner `@s2n2`.
Keep `custom_components/dobby_scheduler/manifest.json` at that exact path. Never
commit Home Assistant backups, credentials, `.storage` files or `secrets.yaml`.

## Release a version

1. Bump `version` in `manifest.json` and `VERSION` in `const.py`, and add a
   CHANGELOG entry.
2. Push to `main` (use git, or GitHub Desktop, rather than the web uploader: the
   web uploader drops the `.github` folder and `.gitignore`).
3. Wait for the **Validate** workflow (HACS, hassfest and tests) to pass.
4. Create a GitHub release with a NEW tag `vX.Y.Z`, e.g. `v0.2.0`. HACS then
   shows a real version number instead of a commit hash. Mark experimental builds
   as pre-releases.

## Install or update with HACS

HACS > Integrations > Dobby Scheduler > Update (or add
`https://github.com/s2n2/roborockHA` as a custom repository of type
Integration). Restart Home Assistant fully. Keep the existing Dobby config entry;
don't create a second one. Refresh the browser/app afterwards. The card loads
automatically from:

```text
/dobby_scheduler_frontend/dobby-scheduler-card.js?v=0.2.0
```

## References

- https://www.hacs.xyz/docs/publish/integration/
- https://developers.home-assistant.io/docs/creating_integration_manifest/

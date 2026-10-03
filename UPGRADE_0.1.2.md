# Dobby Scheduler 0.1.2 - card exists in picker but cannot be instantiated

## What the reported evidence establishes

The user's browser reported `cardRegistered: false`,
`defaultConfigAvailable: "undefined"`, and one Dobby picker entry. That means a
catalogue entry is present while the current custom-element registry has no
Dobby constructor. It is not a typo in the Manual card's type.

The supplied 0.1.1 JavaScript registers the constructor immediately, then adds
picker metadata. HA's app entrypoint imports its scoped custom-element registry
polyfill before its home-assistant root. If an automatically loaded extra module
runs earlier, it can register in the old native registry and capture the old
HTMLElement class. The later registry then cannot resolve it, while picker
metadata remains. This is consistent with HA frontend issue #52960 and was
reproduced with simulated registry replacement. The user's actual startup was
not instrumented, so this is the leading diagnosis, not direct observation of
that exact registry replacement on their machine.

## Fix

The card bootstrap now waits for `home-assistant` before declaring the Dobby
class or registering the element. It checks the current registry again after
waiting, keeps duplicate imports idempotent, and advertises the picker entry
only after registration succeeds. No global registry monkey-patching or
changes to other cards are used in production code.

Automatic loading remains enabled. No manual Lovelace resource is needed.
The automatic URL is versioned as `?v=0.1.2`.

## Upgrade via GitHub and HACS

1. Back up HA and pause automatic cleaning during the update.
2. Upload the CONTENTS of this archive to the root of `s2n2/roborockHA`, merging
   any separate changes you have made. The live repository could not be fetched
   during this patch; the supplied 0.1.1 archive is its baseline.
3. Commit, then publish a NEW GitHub release/tag `v0.1.2` (experimental).
4. HACS: update repository information, redownload/update to `v0.1.2`, then fully
   restart Home Assistant. Updating metadata alone does not replace installed files.
5. Fully refresh the frontend or close/reopen the app. A fresh private browser
   window is useful to distinguish a stale client from current installed code.
6. Keep the existing integration entry, helper entities, labels, maps, to-do
   queue and dashboard card. Do not recreate them. Remove an obsolete manual
   Dobby Resources entry if still present; automatic loading provides the module.

Manual card configuration remains:

```yaml
type: custom:dobby-scheduler-card
title: Dobby
```

## Check the new card is loaded

Browser console, after the HA page finishes loading:

```javascript
({
  cardRegistered: !!customElements.get("dobby-scheduler-card"),
  version: customElements.get("dobby-scheduler-card")?.version,
  bootstrap: window.dobbySchedulerCardStatus
})
```

Expected: `cardRegistered: true`, `version: "0.1.2"`, and bootstrap stage
`registered`. The new script also logs `[Dobby Scheduler 0.1.2] Card registered...`.
`waiting-for-home-assistant` indicates the root is not ready; `failed` includes
an error. This check reads browser state and does not control the robot.

## Temporary recovery on 0.1.1

After the Home Assistant page has finished loading, this imports the existing
card file from the SAME Home Assistant origin with a new URL. It re-runs only
card registration; it does not issue a robot cleaning command.

```javascript
import("/dobby_scheduler_frontend/dobby-scheduler-card.js?recovery=" + Date.now())
  .then(() => console.log(
    "Dobby registered:",
    !!customElements.get("dobby-scheduler-card")
  ))
  .catch(error => console.error("Dobby card reload failed:", error));
```

If it reports true, leave the page loaded and reopen the card editor. This is a
single-page recovery, not a persistent update. Do not disable browser security
controls. If it fails, the exact exception is diagnostic; do not repeatedly add
resource entries or delete the integration.

## Scope and validation

Production changes relative to 0.1.1 are the dashboard JavaScript, release
constants, and manifest version. All other Python runtime files are byte-for-byte
unchanged. Scheduler state/storage schema and existing entity identities are
unchanged. This does not migrate or reset data.

- 107 Python scheduling/adapter/bootstrap simulation tests passed.
- 11 Node registration regressions passed, including reproducing the old symptom.
- 21 existing Chromium UI checks passed.
- 5 new Chromium startup/registry-swap checks passed, including actual card
  construction after the simulated replacement.
- JavaScript syntax, Python compilation and offline repository checks passed.

The registry tests model HA's replacement; they do not bundle the actual scoped
registry polyfill. The browser UI backend is mocked. No live HA instance,
credentials, user's home address or physical robot was accessed. HACS/hassfest
and the supervised robot acceptance checklist remain separate checks.

Primary references:
- https://github.com/home-assistant/frontend/issues/52960
- https://github.com/home-assistant/frontend/blob/dev/src/entrypoints/app.ts
- https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/
- https://www.hacs.xyz/docs/publish/integration/
- https://www.hacs.xyz/docs/use/repositories/dashboard/

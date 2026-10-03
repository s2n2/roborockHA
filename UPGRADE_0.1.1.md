# Dobby Scheduler 0.1.1 - fixing helper-only visibility and card discovery

## Confirmed in the supplied v0.1.0 archive

The manifest declared `integration_type: helper`. The original package therefore
classified this multi-entity scheduler as a helper, not the service integration
intended by its installation instructions.

The dashboard script already registered `window.customCards`, but the backend
only served the file. A manually configured JavaScript module resource was needed
before a browser could discover the card. HACS installing the files was not
sufficient to execute the card script.

## Changes

The manifest now declares `service`. Home Assistant's `frontend` dependency is
loaded before Dobby, and `frontend.add_extra_js_url` registers the card as an ES
module. No Lovelace configuration or .storage data is directly edited. The domain,
entry identifiers, entity identifiers and queue storage schema are unchanged.
The card picker registration is safe to run more than once.

## Apply through GitHub/HACS

1. Back up HA and pause automatic Dobby cleaning.
2. Upload the contents of this archive to the root of s2n2/roborockHA. Review any
   changes you made since v0.1.0 first. Check the GitHub validation workflow.
3. Publish a NEW release/tag v0.1.1 (experimental/pre-release is appropriate).
   Do not move the old v0.1.0 tag to new code.
4. In HACS, open Dobby Scheduler, use Update information, then Redownload and
   select v0.1.1. If using pre-releases, enable them for this repository.
5. Restart Home Assistant fully. Do not delete the existing integration entry,
   queue or helper entities, and do not add another entry.
6. Remove an OLD MANUAL Dobby resource entry from Dashboard Resources if one
   exists. The new automatic module needs no Resources row. Refresh the browser
   completely (Ctrl+F5 on Windows), or fully close/reopen the companion app.
7. Find Dobby Scheduler in Settings > Devices & services > Integrations, then
   edit your dashboard and choose Add card > By card > Dobby Scheduler.

Manual card configuration still works:

```yaml
type: custom:dobby-scheduler-card
title: Dobby
```

## Temporary workaround while still on v0.1.0

In Settings > Dashboards > Resources, add this once as JavaScript module:

```text
/dobby_scheduler_frontend/dobby-scheduler-card.js?v=0.1.0
```

Enable Advanced Mode in your profile if the Resources option is hidden. Refresh
Home Assistant, reopen the By card picker, or add the Manual card shown above.
The integration will remain classified as a helper until its manifest is updated
and HA is restarted. Do not create additional Dobby entries to work around that.

A 'Custom element does not exist: dobby-scheduler-card' error means the card's
module did not load or execute in that browser. A Dobby 'not loaded' message inside
the rendered card instead means its backend entry is not available. For a remaining
issue, capture the precise error and Dobby's Home Assistant log entries.

## Scope

Nothing was published to GitHub or applied to the user's HA by this preparation.
The live repository could not be fetched; the supplied HACS-ready v0.1.0 ZIP is
the source for the fix. See TESTING.md for tests and limitations.

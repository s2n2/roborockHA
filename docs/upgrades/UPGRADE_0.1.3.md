# Dobby Scheduler 0.1.3 - card and setup layout

This is a presentation update based on the supplied 0.1.2 repository archive.
The live GitHub repository was not retrievable during preparation. Review/merge
any independent repository changes before replacing files.

## What is fixed

The old summary used three grid tracks with content-based minimum widths. Long
text could crowd out adjacent values. The small-screen rules also depended on
viewport width, so a narrow card on a large desktop did not get the intended
layout. The new card uses zero-minimum tracks and card-width container queries.

- Next room occupies a separate row on narrow cards; battery and completion
  stay readable. Room names wrap instead of covering adjacent controls.
- Configure rooms has its own button below the setup text.
- Run and dock actions remain aligned; daily defaults sits by the room picker.
- Old-automation warnings remain visible and now have a Review button.
- Setup has a fixed header/tab area and a separately scrolling form.
- Narrow setup dialogs use a room dropdown rather than a crowded side list.
- Colours follow the Home Assistant theme; light and dark layouts are tested.
- Automatic-when-away is still the same backend switch, shown as a toggle.

The package does not invent battery readings, label rooms automatically or hide
missing setup. Unknown battery / no configured rooms still require robot/room
setup. The automatic scheduler starts disabled as before.

## Apply via your existing HACS repository

1. Back up Home Assistant. Upload/merge the extracted repository contents into
   the root of `s2n2/roborockHA`. Do not upload the ZIP as the only repository file.
2. Create a new GitHub release/tag `v0.1.3` from that commit. Do not move old tags.
3. In HACS, update repository information and actually download/update Dobby
   Scheduler to `v0.1.3`. A metadata refresh alone does not replace files.
4. Fully restart Home Assistant, then refresh/reopen the browser/app.

Do not delete the integration, helpers, room mappings, labels or queue. Keep
existing cards. Do not add a second manual dashboard resource: automatic loading
is retained, with a new `?v=0.1.3` cache key.

The card YAML remains:

```yaml
type: custom:dobby-scheduler-card
title: Dobby
```

If the previous card's Sections Layout tab was given a fixed row height manually,
that dashboard override can still constrain it. Restore automatic height there.
The new card itself no longer requests a fixed ten-row height.

## Alternative: minimal patch for an existing 0.1.2 checkout

The patch ZIP contains only these three runtime files and this guide:

- `custom_components/dobby_scheduler/frontend/dobby-scheduler-card.js`
- `custom_components/dobby_scheduler/const.py`
- `custom_components/dobby_scheduler/manifest.json`

It is not a standalone install and is not a replacement for the full repository.
Apply over 0.1.2, publish the new release, then follow the same HACS/restart steps.
The full repository ZIP additionally updates docs, tests and preview images.

## Confirm the displayed build

After refreshing, this read-only browser-console check should return `0.1.3`:

```javascript
customElements.get('dobby-scheduler-card')?.version
```

The working registration wait from 0.1.2 is unchanged apart from version text.
No scheduler runtime code, storage schema, room map or command API was changed.
See `docs/runtime_change_audit_0.1.3.json` for exact changed runtime files.

## Test scope

107 Python scheduling/adapter/setup simulations passed; 11 Node registration
checks passed; 26 existing Chromium UI/startup checks and 102 additional layout
assertions passed. New checks cover empty and populated cards, long room names,
300/340/380/520/720-pixel desktop columns, 360/390/768/1440-pixel popup viewports,
light/dark themes, scrolling headers, Area selection, and oversized inherited text.
No browser JavaScript errors were observed in those mocks.

These are simulations with a mock Home Assistant API and icon renderer, not a
live Home Assistant/Dwains dashboard, Roborock or device test. Existing hardware
acceptance requirements remain. Nothing was installed or pushed remotely.

## References

- https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_containment/Container_queries
- https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/
- https://www.hacs.xyz/docs/publish/integration/
- https://www.hacs.xyz/docs/use/repositories/dashboard/

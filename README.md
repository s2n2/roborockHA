# Dobby Scheduler 0.1.6

## 0.1.6: keep cleaning when a water tank needs attention

Confirmed configured water-tank alerts now make mop and vacuum+mop rooms run
**vacuum-only** by default. The mode is confirmed before dispatch; labels remain
unchanged. A mid-run shortage docks the robot before a fresh dry attempt. The
queue explicitly records **Vacuumed only - mop skipped** after normal successful
clean/dock/empty verification, rather than claiming the room was mopped.

The option is in **Robot & schedule**, beneath the water-problem inputs.
Unknown water readings and unrelated robot faults are not ignored. After an
upgrade, a saved water fault needs **Retry after checking** once while docked.
See [UPGRADE_0.1.6.md](UPGRADE_0.1.6.md) for exact behaviour and installation.

## 0.1.5: reusable robot activity and one-minute room confirmation

New `sensor.dobby_scheduler_activity` reports Cleaning Kitchen, Returning to dock,
Main brush jammed and other observed robot states, independently of the scheduler.
`sensor.dobby_scheduler_room_stable` publishes only room names reported unchanged
for the confirmation window (60 seconds by default). Neither is job-completion
proof. Configure sources and the delay in Robot & schedule -> Activity & room
history. No extra per-device YAML is required.

Use the Activity sensor as the sole target in `dashboard-activity-card.yaml` for
quiet room history with immediate error/dock updates. Read
[UPGRADE_0.1.5.md](UPGRADE_0.1.5.md) for filter semantics, setup and update steps.


## 0.1.4: single press, one cycle, or two cycles

Configure inputs under **Buttons & switches** using `dobby_room_press`,
`dobby_room_toggle` (two changes), or `dobby_room_double_toggle` (four changes).
The accepted request is saved then acknowledged with Locate (enabled by default).

**Existing `dobby_room_toggle` labels now mean ONE cycle.** Change them to
`dobby_room_double_toggle` to retain the previous two-cycle behaviour.
Read [UPGRADE_0.1.4.md](UPGRADE_0.1.4.md) for supported button/event types and
migration. The responsive layout and delayed frontend registration are retained.

A label-driven, room-by-room Roborock scheduler for Home Assistant, with a native ordered to-do queue and a self-contained dashboard card.

**This is a custom integration bundle, not a YAML-only automation.** Copy the integration folder once. The optional YAML package creates its integration entry; it does not contain room/device lists. Configure the robot, rooms, labels, map numbers and priorities through the card's setup pop-up afterwards.

**Initial automatic scheduling is OFF.** Nothing moves merely because the integration loads. Review mappings, stop competing schedules and complete supervised tests before enabling unattended runs.

This is an initial, locally tested build. The Python controller and browser card were tested with simulated inputs, not inside a running Home Assistant installation or on a physical robot. It is not an official Home Assistant/Roborock product and this repository is not automatically included in the HACS default catalogue.


## Card startup fix retained from 0.1.2

Upgrading from 0.1.1: see [UPGRADE_0.1.2.md](UPGRADE_0.1.2.md). The bundled
card now waits for Home Assistant's root element before defining the card class
and registering it. This avoids the extra-module/scoped-registry startup race
where the picker entry exists but `customElements.get()` returns undefined.
The card still loads automatically. No helpers, queue items, labels, maps or
scheduling logic need to be recreated. A full frontend refresh is required.

## What is included

- Dynamic room picker from Home Assistant Areas with `dobby_cleanable`.
- Native `todo` entity: persistent ordered jobs, descriptions, editable notes and completed state. No separate Local To-do integration is required.
- Genuine queue ordering, including up/down arrows and Make next. No artificial due times.
- Mopping-first default-order tool; adjustable per-Area priorities; nightly restoration of `dobby_daily` Areas.
- Labelled single presses, one-cycle or two-cycle switch gestures promote their Area to next and request Locate feedback. Different inputs cannot combine into one gesture.
- Vacuum / vacuum-and-mop / mop labels. Mode is confirmed before starting each room.
- One room job at a time, return to dock and confirmed dust-emptying before the next job.
- Presence interruption: dock when someone arrives, keep the room pending, restart it after the next confirmed absence.
- An in-card more-info-style setup dialog for rooms, live map-number lookup, label editing, robot entities, schedule, gestures, instructions and diagnostics. It does not replace Home Assistant's global more-info dialogs.
- Status/pending/completed entities and automation actions usable elsewhere.
- No Browser Mod, Pyscript, AppDaemon, MQTT broker, extra Python dependencies or external frontend assets required by this bundle.

## Compatibility

Use the **official Roborock integration**, with a V1 robot supporting `app_segment_clean`, a cleaning-mode selector, and the applicable dock controls. This is not a universal scheduler for every vacuum brand or Roborock protocol.

The application targets current Home Assistant APIs inspected in October 2026. Your exact Home Assistant release and robot firmware have not been certified. Check the Diagnostics tab before use. The card uses modern browser features including a native HTML dialog.

A correct successful-clean result is essential: Home Assistant's generic `docked` state can also represent mop washing or emptying. The included read-only adapter inspects the existing official Roborock coordinator's cached last-clean record. **That is an internal compatibility dependency.** If its layout or required fields are unsupported, the scheduler blocks automatic starts/completion rather than assuming success. A last-clean timestamp by itself is not sufficient.

The integration does not establish a new robot connection or request credentials. It uses your existing Roborock integration, which can still depend on Roborock cloud services, including map retrieval.

## Install with HACS (custom repository)

Repository: `https://github.com/s2n2/roborockHA`, category **Integration**.

1. Download Dobby Scheduler in HACS and restart Home Assistant.
2. For a NEW installation only, open Settings > Devices & services > Add
   integration > Dobby Scheduler. Do not add a second entry when upgrading.
3. Refresh the Home Assistant browser/app completely. The integration loads its
   bundled JavaScript automatically using Home Assistant's frontend module API.
   It does not edit your dashboard or require a manual Resources entry.
4. Edit a dashboard, choose Add card > By card, and search for **Dobby Scheduler**.
   Alternatively use the Manual card below.
5. Open the card's gear button to configure rooms and the robot. Keep automatic
   scheduling off until supervised acceptance checks pass.

```yaml
type: custom:dobby-scheduler-card
title: Dobby
```

Dobby now uses integration type `service`, so it belongs in the Integrations
screen rather than the Helpers screen. Existing config entries and entity IDs
are reused; the queue and settings are not reset by this change.

## Upgrading from 0.1.0

Back up Home Assistant and pause Dobby's automatic scheduler before updating.
Update the files through HACS and restart Home Assistant fully. Reloading the
integration alone will not reread its manifest classification.

Do NOT delete Dobby's existing entry or its queue/helpers and do not add another
entry. After the restart, refresh the browser/app and reopen Add card. If you
previously added a Dobby resource under Settings > Dashboards > Resources,
remove that one manual Dobby resource entry: version 0.1.1 loads it automatically.
Do not remove other cards' resources or a Dobby card already on your dashboard.
This release guards against duplicate picker registration during the transition.

The automatic module is:

```text
/dobby_scheduler_frontend/dobby-scheduler-card.js?v=0.1.4
```

This is an integration-provided frontend module, so it need not appear as a
stored row in the dashboard Resources editor. The URL is also useful for checking
that the integration serves its JavaScript; open it on your own Home Assistant
address. A 404 means the HTTP path is not loaded; review Home Assistant logs.

## Install manually

1. Copy `custom_components/dobby_scheduler/` into
   `/config/custom_components/dobby_scheduler/`, with `manifest.json` directly
   inside that directory, and restart Home Assistant.
2. For a new installation, use Settings > Devices & services > Add integration >
   Dobby Scheduler. Alternatively, when packages are already enabled, copy
   `packages/dobby_scheduler.yaml` to `/config/packages/` before restarting.
   Use ONE setup route, not both. Existing installations keep their current entry.
3. Refresh the browser/app, add the Dobby Scheduler card shown above, and configure
   it using the gear button. No extra manual resource entry is needed.

Room mappings, labels, order and connection settings need no subsequent YAML edits.
A new room needs one-time Area/mapping confirmation in the pop-up. A replacement
wall switch in an already mapped room needs its correct Area and gesture label.

## First setup in the pop-up

### Robot & schedule

Select the vacuum, then click **Find controls for this vacuum**. This suggests existing entities whose names match the selected vacuum; check each suggestion, including any renamed entities, and Save settings. It does not enable cleaning.

Required sources are: the vacuum, an on/off presence entity (`on` means someone home), cleaning-mode selector, vacuum-error sensor, and battery reading (a configured battery sensor or the vacuum's `battery_level` attribute). Select the current-map selector if exposed. Configure the dust-emptying switch when using empty-after-room, and the mop-washing switch on a mop-washing dock. Without a map selector, the adapter must supply a current map ID.

Water-problem sensors are on/off tank inputs with `on = problem`. By default, confirmed tank alerts make wet jobs vacuum-only for that run; unavailable inputs still block wet jobs. Disable the fallback in Robot & schedule to restore strict water blocking. Add optional pause helpers such as a babysitter, holiday or manual-block helper. Any configured blocking helper that is on or unavailable prevents running. It does not silently infer children/guests from two adults being away: your presence entity must reflect the household policy you want.

Defaults: 15-minute absence, 40% minimum battery, 08:00-21:00 cleaning window, 00:05 nightly reset, two-second gesture window, five-second gesture cooldown. Times use Home Assistant's local timezone. Run now bypasses the absence delay, not the cleaning window or hardware/mapping checks; it asks before running while someone is home.

### Rooms & map

Create the eight labels using the button (or create only the missing ones when upgrading). Existing labels with the same name/ID are reused. Unrelated labels are preserved.

With the robot docked and no scheduler job active, click **Fetch/check maps**. This calls `roborock.get_maps` and reads map names, flags and room numbers; it does not start cleaning or switch maps.

Select a Home Assistant Area. Choose its map and one or more segment numbers, compare them to the actual Roborock map, then tick **I checked these numbers**. Enable Available to Dobby, Daily default if wanted, and exactly one cleaning-mode label. Set a default priority and Save this room.

The selected map on the robot must match the job's stored map. The scheduler never changes maps automatically. A segment must not belong to two cleanable Areas. Changing segment selections clears the verification tick. A new map fetch detects missing segments and renamed mapped rooms; re-check before saving. **Refresh and re-verify after editing/splitting/merging maps.** The cached mapping cannot automatically prove an unchanged number still represents the same floor geometry.

Several segments can form one job/Area, but all share that Area's mode and are treated as a single completed room. Use separate Areas for hallway carpet and hallway tiles when their cleaning modes differ. Assign a wall input's entity Area appropriately; this can override the device Area.

**Use mopping-first defaults** proposes wet rooms first, with an Area named Kitchen and wet Areas containing Hallway at the front. It displays the proposed order for confirmation and saves numbered priorities. Other household names can be ordered using the numeric priorities. It changes tomorrow's defaults, not today's list; use Daily defaults to apply them to today's queue.

### Labels

| Label | Where | Meaning |
|---|---|---|
| `dobby_cleanable` | Area | Show this Area as a selectable cleaning room |
| `dobby_daily` | Area | Add the room on each nightly reset |
| `dobby_vacuum` | Area | Vacuum only |
| `dobby_vacuum_mop` | Area | Vacuum and mop |
| `dobby_mop` | Area | Mop only |
| `dobby_room_toggle` | One on/off input entity | One complete cycle, two changes |
| `dobby_room_double_toggle` | One on/off input entity | Two cycles, four changes |
| `dobby_room_press` | Momentary input, button or event entity | Single press; `room_press` alias accepted |

Only one mode label per Area. No mode label defaults to vacuum, with a warning in room metadata. Conflicting mode labels block the room until corrected. Label changes outside the card also refresh the scheduler's Area list.

### Buttons & switches

Select an input and one of the three gestures in the setup pane. A complete
switch cycle returns to its starting state. Single-press mode accepts a rising
edge for momentary on/off inputs or a fresh button/event timestamp. For event
entities, common short-press types are recognised; the UI also permits an exact
vendor-specific event type. One gesture label per input; conflicts are blocked.

The entity Area overrides the device Area. Raw event-only buttons can be
bridged through an input_button helper using a standard HA UI automation.
No per-device YAML is required for inputs already exposed as supported entities.
See the upgrade guide for restoration filtering, cooldown and bridge limitations.

All accepted input requests save the queue and call vacuum.locate when Locate
acknowledgement is enabled (default ON). DND/volume/firmware may suppress the
sound. Failure is logged without deleting the job. An active room is not
requeued. Existing pending rooms are promoted without duplicates; completed
rooms can be requested again. No lights are flashed and a request does not
bypass the scheduler's presence/window/safety rules.

## Daily use

Tap room chips to add/remove today's selections. Completed rooms can be tapped to request another run. In the execution list, use Make next or up/down arrows. You can also add/remove/promote the selected room from the setup pop-up. An urgent request becomes the next job after the active room, not an interruption.

Daily defaults rebuilds the queue from current daily labels in saved priority order. Nightly reset does the same automatically, clears yesterday's ad-hoc requests/completed state, and resets temporary promotions. A reset due during an active job is deferred; after a missed reset or restart, the next local cleaning day is reconciled. Normal ordering uses the saved priorities; cleaning mode never secretly overrides an urgent or manually reordered queue.

Enable Automatic when away only after testing. The configured absence must be continuous and known. When someone returns during an owned job, it is sent to the dock and left pending. Once the house is away again for the delay, the room can start from the beginning. A Home Assistant restart also leaves an in-flight room pending and docks it conservatively; it never restores a permission override to clean while someone is home.

The scheduler changes the room's cleaning mode before issuing the one-room job and waits for it to be reported. It optionally sets the configured mop intensity only for wet jobs. **It never explicitly starts a mop wash.** Dock firmware still decides when automatic washing is needed; selecting vacuum cannot guarantee that no firmware-initiated washing occurs.

## Completion, emptying and recovery

Automatic completion requires all of:

- This scheduler owns the room job and observed it enter cleaning.
- A new last-clean record matches the command's time/map and reports `complete=1`, `error=0`, and positive cleaned area.
- No tracked interruption invalidated the job.
- The robot is docked and dock washing is no longer active.
- Required dust-emptying is confirmed by an observed on/off cycle or an increase in the dock's dust-collection counter.

Mop washing during an unfinished job is not success. Returning to recharge or a cancelled record is not success. A timeout is never success. If auto-emptying is already observed, the scheduler avoids issuing it again; otherwise it requests emptying and waits. Do Not Disturb is never turned off to force an empty or a voice acknowledgement.

Faults are latched for inspection instead of silently retrying commands indefinitely. A service timeout can mean the robot received the command even though HA did not receive a result. The robot may still be moving: inspect it or press Pause & dock. Retry is allowed while docked. A proved successful clean can retry only its dock service rather than clean the same room again. Manually confirm cleaned is an explicit, logged user override allowed while docked; it is not labelled as an automatic successful robot report.

**Do not run native robot-app schedules, other room scripts or whole-home clean commands concurrently.** Other HA commands are detected where their target can be identified. Commands from the robot app or physical robot buttons are not completely observable, and a successful record does not prove exclusive ownership at the protocol level. One controller at a time is a requirement, not a promise this integration can enforce across all apps.

## Native entities and actions

Typical first-install entities:

```text
todo.dobby_scheduler_queue
sensor.dobby_scheduler_status
sensor.dobby_scheduler_pending
sensor.dobby_scheduler_completed
switch.dobby_scheduler_enabled
```

The status sensor carries current/next room, wait reason, fault, cleaning day and backend diagnostic information. HA may suffix entity IDs if these already exist; the bundled card gets the actual IDs from the backend. There is one scheduler instance in this version.

`dobby_scheduler.enqueue` accepts `area_id` and optional `urgent`. Actions also include `run` (optional `allow_home`), `pause`, `reset`, `retry`, and `enable` (boolean `enabled`). See `services.yaml` or Developer tools > Actions. No room IDs need to be embedded in an automation using enqueue.

The native to-do integration allows genuine item movement. Its descriptions contain readable structured metadata plus an editable note. Area names and routing/mode metadata are authoritative in the registry/setup, not in arbitrary edited to-do descriptions. To-do checkboxes are manual confirmations; automatic completion is handled by the scheduler.

## Migration, sharing and privacy

Read `docs/MIGRATION.md` before enabling. Existing automation files are not overwritten by installation. The diagnostics button can disable only the specific recognised old Dobby scheduling automations after confirmation, not delete them. It cannot find every custom schedule or Roborock-app routine for you.

The ZIP is household-neutral; it contains no robot account credentials or exported private configuration. You may share it under the included MIT licence. Each recipient installs the official Roborock integration separately and configures their own entities, Areas and mappings in the pop-up. HACS updates are available after a maintainer publishes this as a custom repository; the default catalogue requires a separate submission. See PUBLISHING.md.

Runtime settings and queue state are saved with Home Assistant's storage helper under `.storage/dobby_scheduler.<entry_id>`. Back up Home Assistant before updating/uninstalling; do not manually edit storage while HA runs. A diagnostic export contains configured entity names, Area/map names, jobs and recent logs. Inspect/redact it before sharing; the card's full entity-candidate list is omitted from exports.

See `TESTING.md` for completed simulations, manual acceptance tests, and limitations. Screenshots in `docs/previews/` are simulated, not images of an installed household dashboard.

## Primary API references inspected

- https://www.home-assistant.io/integrations/roborock/
- https://developers.home-assistant.io/docs/core/entity/todo/
- https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/roborock/vacuum.py
- https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/roborock/coordinator.py
- https://github.com/Python-roborock/python-roborock/blob/main/roborock/data/v1/v1_containers.py
- https://developers.home-assistant.io/blog/2024/06/18/async_register_static_paths/
- https://www.home-assistant.io/docs/configuration/packages/

These are upstream references, not claims of endorsement, certification or long-term internal API stability.

## Publisher files

See [PUBLISHING.md](PUBLISHING.md) for repository setup, HACS installation and releases.
Publishing validation workflows are included; passing them is not a live robot test.

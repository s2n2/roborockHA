# Architecture and maintenance

The pure `engine.py` state machine owns the queue and returns side-effect descriptions. It does not call HA or a robot. `controller.py` serialises changes behind an asyncio lock and commits state with HA's Store **before** normal state-machine side effects are sent. Long waits are represented as phases, not blocking sleeps. The controller listens to relevant HA state/registry changes and also checks every five seconds; it does not force a five-second cloud poll.

The native todo platform exposes that same ordered queue; it is not a synchronised copy of a second list. The card and native todo operations reach the same controller. Persisted job IDs are generated UUIDs. Queue job content is distinct from Area configuration and labels: relabelling changes future mode selection without redefining per-switch YAML.

The browser uses authenticated `dobby_scheduler/get` and `dobby_scheduler/command` WebSocket endpoints. Registry, map, settings and legacy-disable operations require administrator permission. Other operations require queue-control permission; reading requires queue-read permission. HA automation actions use the caller's context where present. The browser escapes dynamic strings and does not load third-party remote code. The setup dialog is a native HTML dialog in the card's shadow root; built-in more-info dialogs are still used only when explicitly opening an entity.

Room routing is stored once in this integration's GUI configuration: HA Area -> approved map flag/name -> selected numeric segments. We deliberately issue the public `vacuum.send_command` segment-cleaning action using that mapping instead of maintaining a second `vacuum.clean_area` mapping. A selected map mismatch blocks; map switching is never automatic.

## Completion adapter

Current Roborock V1 supports a cached clean summary with a `last_clean_record` carrying begin, end, complete, error, area and map flag. The adapter reads the vacuum entity's coordinator when accessible, otherwise matches the coordinator from its configuration entry by device identifiers. It does not choose the first robot on an account or instantiate another Roborock API client.

This cached-data structure is **internal**, not a guaranteed public HA service. Required fields are checked. An unsupported layout fails closed. The optional configured external completion sensor is an escape hatch for a reviewed adapter, not a recommended substitute based on timestamps alone. Its attributes must carry a real per-job success result.

Completion is correlated by command timing, map identity, observed cleaning, and no tracked interruption. Firmware/app commands outside HA can still invalidate exclusive ownership without a detectable HA service event. Concurrent controllers must be disabled. A reported successful room clean is not proof of spotless floors or that every square metre was physically accessible.

A robot's `dust_collection_count` increase can confirm a short automatic emptying cycle that HA's state sampling missed. Otherwise the emptying switch must be observed on then off. Neither an arbitrary delay nor an off switch at baseline counts as a completed empty.

## Testing/development

Runtime Python requirements are empty; the integration uses Home Assistant's existing modules. The standalone engine tests use pytest, and frontend tests additionally use Playwright with Chromium. The HA adapter tests supply explicit mock registries/services; they do not constitute real HA runtime tests or hassfest validation.

```sh
pytest -q tests/test_engine.py tests/test_adapter.py
python tests/test_frontend.py
python -m compileall -q custom_components/dobby_scheduler
node --check custom_components/dobby_scheduler/frontend/dobby-scheduler-card.js
```

An installed system's logs and in-card diagnostic snapshot are needed to establish actual version/hardware compatibility. Never weaken the completion predicate simply to make a blocked queue appear to work.

## Immediate gesture permissions (0.1.7)

`Engine.gesture_requests` is a runtime UID-to-request-time map, never exported to
storage. Only the validated physical/button handler calls `request_immediate`.
Neither job.source nor urgent nor arbitrary to-do-description metadata grants
permission. The pending queue is stably partitioned into authorised requests and
ordinary work, with fresh requests promoted within the first tier. Occupied-house,
away-delay, automatic-enable and window exceptions apply to the job, not to the
whole engine's `manual`/`allow_home` flags. The active job remains non-preemptive.

A failed gesture save rolls back jobs, grants and reset/log state. Dispatch is
kicked before awaiting Locate, still after a successful persist. State-machine
robot effects continue to be persisted before execution. A routine arrival/window
interruption of ordinary work preserves other freshly requested rooms; real
safety aborts, explicit Pause, resets and restart cancel immediate permissions.
Water-fallback redocking preserves the current batch, with the usual readiness
checks. Keep these invariants covered by tests/test_immediate_priority*.py.

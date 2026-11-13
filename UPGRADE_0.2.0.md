# Dobby Scheduler 0.2.0 - No blocking errors

## What changes

Earlier versions latched most problems as a fault and refused to run again until
**Retry after checking** was pressed. 0.2.0 removes that step.

| Problem | 0.1.9 | 0.2.0 |
|---|---|---|
| Failed command (set mode, clean, dock, empty) | Latched until Retry | Logged; robot docks; room pending; queue carries on after ~2 min |
| No successful clean record after docking | Latched until Retry | Logged; room pending; retried later |
| Cleaning never confirmed / room time limit / connection lost | Latched until Retry | Same as above |
| Dust emptying not confirmed after a proved clean | Latched until Retry | Room completed, noted "empty not confirmed" |
| Internal scheduler error | Schedule switched off + latched | Logged; schedule stays on |
| Vacuum or dock error reported by the Roborock | Latched until Retry | Shown on the card while present; Dobby resumes when it clears |
| Error sensor unavailable | Latched (mid-run) | Waits at pre-flight; not shown as a fault |

A room that fails 3 times in one day is skipped so one bad room cannot loop all
night. Requesting it again (dashboard, switch/button, to-do) or the next daily
reset gives it fresh attempts. The retained `dobby_scheduler.retry` service does
the same for all skipped rooms.

## Upgrading

- Any fault saved by an older version is cleared on first start.
- No settings change. The 0.1.9 APP_CHARGE auto-check is superseded.
- Automations reading the status sensor's `fault` attribute: it now holds only
  Roborock-reported errors. Dobby's own last problem is in `last_issue`.

## Check after installing

1. With the robot docked, confirm the card shows no Retry button.
2. Optional: trigger a harmless Roborock error you can clear safely (e.g. lift
   the dustbin while docked if your model reports it). The card should show it
   and Dobby should resume by itself once the vacuum clears it. Don't jam the
   robot or create unsafe faults to test this.

# Migrating from other Dobby automations

Install disabled. Check the map first. Do not layer two automatic vacuum schedulers on the same robot.

This integration recognises these older Dobby automation names (and their original IDs) as conflicts when they are enabled:

| Automation | Original ID |
|---|---|
| Dobby - Clean daily when noone is home | 1724537369968 |
| Dobby - Go back to dock when we arrive home | 1724537691707 |
| Dobby has done cleaning today, don't clean again | 1724629183182 |
| Dobby - new day, reset him to clean today | 1724629252829 |
| Reset Dobbys map to saved one | 1724881864606 |

The card shows the actual matching enabled entities. Its **Disable these old Dobby automations** button requires administrator permission and a confirmation. It calls `automation.turn_off` with `stop_actions: true` only for the displayed matches. It does not delete anything or alter the original YAML files.

Also review manual/custom room-cleaning scripts, floor-plan actions and native Roborock schedules. Those can bypass this queue. A floor-plan click should eventually call `dobby_scheduler.enqueue` with its HA Area, rather than directly launching a competing vacuum job. Existing error-display and maintenance notifications may remain if they do not issue robot/map commands.

Do not delete the old `dobby_should_clean_today` helper or selected-room script until all other references have been checked. This bundle does not depend on them.

Do not merge historical room-number tables automatically. They may describe different maps or versions of a floor plan. Use Fetch/check maps, compare the selected robot map to the actual layout, and confirm each Area mapping.

## Alarms and household presence

A robot can trigger indoor motion detection. Review your alarm rules before unattended runs. This integration does not disarm an alarm or suppress PIRs. Configure any needed alarm policy separately and test it; there is no universal safe alarm bypass.

Use a presence entity that correctly includes children, guests and babysitters as required. Optional pause entities can block cleaning for a babysitter or holiday mode. An unavailable configured presence or blocking entity is not assumed safe to run.

## Rollback

Pause & dock the robot. Disable/remove the Dobby Scheduler integration entry and remove its optional package bootstrap so it is not re-imported. Remove the card/resource and integration folder only after restart/backup as appropriate. Re-enable the old scheduler only after the new one is stopped. Integration storage is not automatically deleted by this initial build; retain it with your backup or remove it only with Home Assistant stopped and after confirming the correct entry ID.

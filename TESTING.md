# Testing

All tests use simulated telemetry and a mocked Home Assistant. They are not a
live Home Assistant or robot test.

```bash
pip install pytest playwright
python -m pytest tests --ignore-glob="*browser*" --ignore=tests/test_frontend.py
node tests/check_card_registration.cjs
# Browser UI scripts need a Chromium binary on PATH named "chromium":
python tests/test_frontend.py
python tests/test_recovery_ui_browser.py   # and the other *_browser.py scripts
```

## 0.2.0 results

- 486 Python tests passed, including 26 self-healing engine tests
  (`test_dock_auto_recovery.py`) and 20 notification/Repairs/settings adapter
  tests (`test_alerts_adapter.py`).
- All 8 browser UI scripts passed in headless Chrome, including 13 new recovery UI
  checks. Node registration checks passed.

## Supervised acceptance for 0.2.0

1. Set a notify action under Faults & notifications and save. While docked, press
   Locate or run one room, and check a normal run still completes, docks and empties.
2. While a room runs, press Pause on the robot itself or lift it briefly so it
   reports an error, then put it back on the dock. The card should show
   **Recovering automatically**, then after the recovery delay the room should be
   retried when the normal schedule allows it.
3. Leave the robot off the dock (no hardware abuse, just don't redock it) for longer
   than the recovery delay + attention time. Check that the **Dobby needs you**
   alert, the Repairs entry and the phone notification appear. Redock it and check
   that all three clear and a "back on track" message arrives.
4. Press Retry on the phone notification while docked and check that the fault clears.

Do not deliberately jam the robot or perform unsafe physical fault tests.
Earlier release notes are in `docs/upgrades/`.

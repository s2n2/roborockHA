# UI 0.1.3 validation

- 107 Python controller, adapter and setup tests passed.
- 11 Node registration checks passed.
- 21 existing Chromium interaction checks passed.
- 5 existing Chromium startup/registry simulations passed.
- 102 new layout assertions passed (see layout-0.1.3-test-results.json).
- JavaScript syntax and offline repository checks passed.
- Runtime byte comparison against the supplied 0.1.2 archive confirms only the
  dashboard script, manifest version and release constants changed.

The new browser test is `tests/test_card_layout_browser.py`; screenshots with
`ui-0.1.3-` prefixes are rendered from that test with a mock HA API and icon
renderer. They are not screenshots of the user's installed dashboard.

Python runtime mock coverage is not an actual HA lifecycle/integration test.
HACS/hassfest hosted CI and physical robot acceptance remain separate checks.

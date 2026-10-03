"""Offline packaging checks. These do not replace HACS, hassfest or live HA tests."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "dobby_scheduler"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-placeholder", action="store_true",
                        help="For inspecting the unpublished template only.")
    args = parser.parse_args()
    manifest = json.loads((INTEGRATION / "manifest.json").read_text())
    hacs = json.loads((ROOT / "hacs.json").read_text())
    errors: list[str] = []
    for key in ["domain", "name", "documentation", "issue_tracker", "codeowners", "version"]:
        if not manifest.get(key):
            errors.append(f"Missing/non-empty manifest key required: {key}")
    if manifest.get("domain") != INTEGRATION.name:
        errors.append("Manifest domain must match integration directory.")
    if hacs.get("content_in_root", False):
        errors.append("content_in_root must be false for this repository layout.")
    if not hacs.get("name"):
        errors.append("hacs.json needs a name.")
    if hacs.get("zip_release", False):
        errors.append("This repository installs from source; do not enable zip_release.")
    dirs = [p.name for p in (ROOT / "custom_components").iterdir()
            if p.is_dir() and not p.name.startswith((".", "__"))]
    if dirs != ["dobby_scheduler"]:
        errors.append("Use one integration per repository.")
    for relative in ["__init__.py", "config_flow.py", "frontend/dobby-scheduler-card.js", "brand/icon.png"]:
        if not (INTEGRATION / relative).is_file():
            errors.append(f"Required bundled file missing: {relative}")
    if "YOUR_GITHUB_USERNAME" in json.dumps(manifest):
        message = "Replace YOUR_GITHUB_USERNAME in manifest.json before publishing."
        if args.allow_placeholder:
            print("UNRESOLVED SETUP:", message)
        else:
            errors.append(message)
    for key in ["documentation", "issue_tracker"]:
        if not manifest.get(key, "").startswith("https://github.com/"):
            errors.append(f"Expected GitHub URL in {key}.")
    for path in INTEGRATION.rglob("*.json"):
        json.loads(path.read_text())
    if errors:
        for message in errors:
            print("ERROR:", message)
        return 1
    print("Offline repository checks passed. HACS/hassfest and live HA remain separate checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

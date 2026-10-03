"""Set public repository metadata locally; does not publish or contact GitHub."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("owner", help="GitHub username or organisation, without @")
    parser.add_argument("--repo", default="roborockHA")
    parser.add_argument("--maintainer", help="Individual GitHub username, if owner is an organisation")
    args = parser.parse_args()
    maintainer = args.maintainer or args.owner
    for label, value in [("owner", args.owner), ("maintainer", maintainer)]:
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", value):
            parser.error(f"Invalid {label}; use a GitHub username without @ or slashes.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.repo) or args.repo in {".", ".."}:
        parser.error("Invalid repository name.")
    path = ROOT / "custom_components/dobby_scheduler/manifest.json"
    manifest = json.loads(path.read_text())
    url = f"https://github.com/{args.owner}/{args.repo}"
    manifest.update(documentation=url, issue_tracker=url + "/issues", codeowners=["@" + maintainer])
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Updated manifest.json for", url)
    print("No remote repository was created or modified.")


if __name__ == "__main__":
    main()

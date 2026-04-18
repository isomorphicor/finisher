from __future__ import annotations

import argparse
import json
from pathlib import Path

from skills.registry_manager import SkillRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="List registered skills from manifest.")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--capability", default="", help="Optional capability filter")
    parser.add_argument("--tag", default="", help="Optional tag filter")
    args = parser.parse_args()

    registry = SkillRegistry(Path(args.repo_root))
    rows = registry.discover(
        capability=(args.capability or None),
        tag=(args.tag or None),
    )
    out = [
        {
            "id": r.id,
            "version": r.version,
            "entry": r.entry,
            "capabilities": r.capabilities,
            "tags": r.tags,
            "trust": r.trust,
        }
        for r in rows
    ]
    print(json.dumps({"status": "success", "report": {"skills": out}}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()


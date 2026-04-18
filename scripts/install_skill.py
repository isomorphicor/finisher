from __future__ import annotations

import argparse
import json
from pathlib import Path

from skills.registry_manager import SkillRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="Install a skill package into skills/installed and registry manifest.")
    parser.add_argument("source_dir", help="Path to skill folder containing skill_manifest.json")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    args = parser.parse_args()

    registry = SkillRegistry(Path(args.repo_root))
    out = registry.install_from_path(Path(args.source_dir))
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()


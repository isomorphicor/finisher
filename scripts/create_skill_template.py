from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _sanitize_skill_id(raw: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", (raw or "").strip()).strip("_").lower()
    return s or "new_skill"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a project-local skill package template.")
    parser.add_argument("skill_id", help="Skill id, e.g. my_skill")
    parser.add_argument("--output-dir", default=".", help="Where to create the skill package folder")
    parser.add_argument("--capability", action="append", default=[], help="Capability entries; can pass multiple times")
    parser.add_argument("--tag", action="append", default=[], help="Tag entries; can pass multiple times")
    parser.add_argument(
        "--permissions",
        action="append",
        default=[],
        help="Optional requirements.permissions entries (file|terminal|network). Can pass multiple times.",
    )
    args = parser.parse_args()

    skill_id = _sanitize_skill_id(args.skill_id)
    out_root = Path(args.output_dir).resolve()
    pkg_dir = out_root / skill_id
    pkg_dir.mkdir(parents=True, exist_ok=False)

    runtime_py = "\n".join(
        [
            "from __future__ import annotations",
            "",
            "from typing import Any",
            "",
            "",
            "def run(runtime, **kwargs) -> dict[str, Any]:",
            '    """Default skill entrypoint template."""',
            "    return {",
            '        "status": "success",',
            '        "report": {"skill": "'
            + skill_id
            + '", "kwargs": kwargs},',
            "    }",
            "",
        ]
    )
    (pkg_dir / "runtime.py").write_text(runtime_py, encoding="utf-8")
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")

    manifest = {
        "id": skill_id,
        "version": "0.1.0",
        "entry": f"skills.installed.{skill_id}.runtime:run",
        "capabilities": args.capability or [f"custom.{skill_id}"],
        "tags": args.tag or ["custom"],
        "trust": "project",
    }
    perms = [p.strip() for p in (args.permissions or []) if str(p).strip()]
    if perms:
        manifest["requirements"] = {"permissions": perms}
    (pkg_dir / "skill_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "success", "report": {"created": str(pkg_dir), "skill_id": skill_id}}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()


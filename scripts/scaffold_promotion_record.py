#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = REPO_ROOT / "docs" / "experiments" / "autonomous_research" / "templates" / "promotion_decision_record.md"
RECORDS_DIR = REPO_ROOT / "docs" / "experiments" / "autonomous_research" / "records"


def _slugify(raw: str) -> str:
    s = (raw or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "promotion"


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a promotion decision record from the template.")
    parser.add_argument("--slug", required=True, help="Short slug, e.g. md-skill-registry-hardening")
    parser.add_argument("--date", default="", help="Override date in YYYYMMDD (default: UTC today)")
    parser.add_argument("--dry-run", action="store_true", help="Print target path only; do not write")
    args = parser.parse_args()

    date = (args.date or "").strip()
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y%m%d")
    if not re.fullmatch(r"\d{8}", date):
        raise SystemExit("Invalid --date, expected YYYYMMDD")

    slug = _slugify(args.slug)
    target = RECORDS_DIR / f"{date}_{slug}.md"

    if args.dry_run:
        print(str(target))
        return

    if not TEMPLATE_PATH.is_file():
        raise SystemExit(f"Template not found: {TEMPLATE_PATH}")

    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise SystemExit(f"Target already exists: {target}")

    content = TEMPLATE_PATH.read_text(encoding="utf-8", errors="replace")
    header = f"<!-- scaffolded: {datetime.now(timezone.utc).isoformat()}Z | template: {TEMPLATE_PATH.as_posix()} -->\n\n"
    target.write_text(header + content, encoding="utf-8")
    print(str(target))


if __name__ == "__main__":
    main()


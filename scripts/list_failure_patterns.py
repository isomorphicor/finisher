#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def _iter_entries(path: Path):
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if isinstance(obj, dict):
            yield obj


def main() -> None:
    parser = argparse.ArgumentParser(description="List failure-pattern stats from knowledge/decision_log.jsonl")
    parser.add_argument("--log-path", default="knowledge/decision_log.jsonl", help="Path to JSONL decision log")
    parser.add_argument("--limit", type=int, default=5, help="Show latest N samples per tag")
    args = parser.parse_args()

    log_path = Path(args.log_path).resolve()
    entries = list(_iter_entries(log_path))
    if not entries:
        print(json.dumps({"status": "empty", "log_path": str(log_path), "patterns": {}}, ensure_ascii=False))
        return

    counter: Counter[str] = Counter()
    samples: dict[str, list[dict]] = {}
    for e in entries:
        tag = str(e.get("failure_pattern") or "").strip()
        if not tag:
            continue
        counter[tag] += 1
        samples.setdefault(tag, []).append(
            {
                "date": e.get("date"),
                "project": e.get("project"),
                "session": e.get("session"),
                "value_score": e.get("value_score"),
                "progress_score": e.get("progress_score"),
                "decision_id": e.get("decision_id"),
            }
        )

    out = {
        "status": "ok",
        "log_path": str(log_path),
        "total_entries": len(entries),
        "patterns": {
            tag: {"count": count, "latest_samples": list(reversed(samples.get(tag, [])))[0 : max(0, int(args.limit))]}
            for tag, count in counter.most_common()
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

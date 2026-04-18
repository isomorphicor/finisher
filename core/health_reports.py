"""Persist autonomy / run-level summaries under the session ``project/outputs/`` tree."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_run_level_health(
    *,
    session_dir: Path,
    out: dict[str, Any],
    attempts: list[dict[str, Any]],
    config: dict[str, Any],
    final_decision: str,
) -> Path:
    """Write ``autonomy_run_health.json`` (and append one line to ``autonomy_run_health.jsonl``)."""
    session_dir = session_dir.resolve()
    out_dir = session_dir / "project" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema_version": "autonomy_run_health_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "final_decision": final_decision,
        "config": config,
        "attempts": attempts,
        "result": out,
    }
    path = out_dir / "autonomy_run_health.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log = out_dir / "autonomy_run_health.jsonl"
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    if log.is_file():
        log.write_text(log.read_text(encoding="utf-8", errors="replace") + line, encoding="utf-8")
    else:
        log.write_text(line, encoding="utf-8")
    return path

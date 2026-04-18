"""JSON handoff + completion checks for external IDE/coder agents (e.g. Cline)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_external_coder_handoff(
    *,
    session_dir: Path,
    external_coder: str,
    task: str,
    refined_task: dict[str, Any] | None,
    include_acceptance: bool = True,
) -> Path:
    """Write ``project/outputs/external_coder_handoff.json`` for the dispatcher / external agent."""
    session_dir = session_dir.resolve()
    out_dir = session_dir / "project" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "external_coder_handoff.json"
    refined = refined_task if isinstance(refined_task, dict) else {}
    payload: dict[str, Any] = {
        "schema_version": "external_coder_handoff_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "session_dir": str(session_dir),
        "external_coder": str(external_coder or "").strip(),
        "task": str(task or "").strip(),
        "refined_task": refined,
        "required_outputs": [
            "project/outputs/execution_report.md",
            "project/outputs/review_gate.md",
            "project/outputs/completion_evidence.json",
        ],
    }
    if include_acceptance:
        payload["acceptance"] = {
            "completion_evidence_must_include": {
                "verification.commands_run": "non-empty list of shell commands actually run",
                "python_or_pytest": "at least one command line must mention python or pytest",
            },
            "read_scheme_artifacts_under": str(session_dir / "artifacts"),
        }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def validate_external_coder_completion(*, session_dir: Path) -> dict[str, Any]:
    """Verify external coder produced execution report, review gate, and completion evidence."""
    session_dir = session_dir.resolve()
    out = session_dir / "project" / "outputs"
    er = out / "execution_report.md"
    rg = out / "review_gate.md"
    ce = out / "completion_evidence.json"
    missing = [p.name for p in (er, rg, ce) if not p.is_file()]
    if missing:
        return {
            "status": "external_coder_incomplete",
            "reason_code": "missing_outputs",
            "message": "required output files missing under project/outputs/",
            "issues": [f"missing: {m}" for m in missing],
        }
    try:
        raw = json.loads(ce.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError as e:
        return {
            "status": "external_coder_incomplete",
            "reason_code": "completion_evidence_invalid_json",
            "message": str(e),
            "issues": ["completion_evidence.json is not valid JSON"],
        }
    if not isinstance(raw, dict):
        return {
            "status": "external_coder_incomplete",
            "reason_code": "completion_evidence_not_object",
            "message": "completion_evidence.json must be a JSON object",
            "issues": ["expected JSON object at root"],
        }
    ver = raw.get("verification")
    if not isinstance(ver, dict):
        return {
            "status": "external_coder_incomplete",
            "reason_code": "verification_missing",
            "message": "completion_evidence.json must contain verification object",
            "issues": ["missing or invalid verification"],
        }
    cmds = ver.get("commands_run")
    if not isinstance(cmds, list) or not cmds:
        return {
            "status": "external_coder_incomplete",
            "reason_code": "commands_run_missing",
            "message": "verification.commands_run must be a non-empty list",
            "issues": ["verification.commands_run empty or not a list"],
        }
    joined = " ".join(str(x) for x in cmds if str(x).strip())
    if not re.search(r"\b(python\d?|pytest)\b", joined, re.IGNORECASE):
        return {
            "status": "external_coder_incomplete",
            "reason_code": "no_python_pytest_command",
            "message": "at least one verification command must mention python or pytest",
            "issues": ["verification.commands_run must include a python or pytest invocation"],
        }
    return {
        "status": "external_coder_completed",
        "reason_code": "external_coder_completion_verified",
        "message": "external coder completion contract verified",
    }

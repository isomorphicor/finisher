from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.adapters.local_adapter import LocalIDEAdapter
from runtime.tool_runtime import ToolRequest

REQUIRED_ARTIFACTS = (
    "research_plan.md",
    "derivation.md",
    "architecture_draft.md",
    "experiment_design.md",
)


def _execution_prep_use_timestamp_subdir() -> bool:
    """If true, nest output under ``…/execution_prep/<UTC>/`` (legacy). Default: stable ``…/execution_prep/``."""
    v = (os.environ.get("INVERST_EXECUTION_PREP_TIMESTAMP") or "").strip().lower()
    return v in ("1", "true", "yes", "timestamp")


def prepare_execution_workspace(
    *,
    scheme_session_dir: Path,
    workspace_root: Path,
    output_subdir: str | None = None,
) -> dict[str, Any]:
    """
    Copy scheme artifacts into a prep folder for IDE work.

    Default output: **inside the scheme session** at
    ``<session>/project/execution_prep/`` (relative to ``workspace_root``), with
    ``scheme/*.md``, ``NEXT_STEPS.md``, ``run_log.json`` directly under that folder.
    Set env ``INVERST_EXECUTION_PREP_TIMESTAMP=1`` to restore a per-run
    ``…/execution_prep/<UTC>/`` subfolder (multiple snapshots).

    If ``output_subdir`` is set, it is interpreted as a path **relative to workspace_root**
    (legacy behavior); the same timestamp flag applies under that base path.
    """
    session_dir = scheme_session_dir.resolve()
    artifacts_dir = session_dir / "artifacts"
    if not artifacts_dir.is_dir():
        return {
            "status": "rejected",
            "report": {},
            "errors": [{"code": "E_ART_DIR", "message": "missing artifacts dir", "details": {"path": str(artifacts_dir)}}],
        }

    missing = [name for name in REQUIRED_ARTIFACTS if not (artifacts_dir / name).is_file()]
    if missing:
        return {
            "status": "rejected",
            "report": {},
            "errors": [{"code": "E_ART_MISSING", "message": "required artifacts missing", "details": {"missing": missing}}],
        }

    # Unified session layout: artifacts/ (scheme) + project/ (implementation & experiments)
    (session_dir / "project").mkdir(parents=True, exist_ok=True)

    wr = workspace_root.resolve()
    adapter = LocalIDEAdapter(wr)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    use_ts = _execution_prep_use_timestamp_subdir()
    if output_subdir and str(output_subdir).strip():
        base = Path(str(output_subdir).strip().strip("/"))
        target_root = base / ts if use_ts else base
    else:
        try:
            rel_session = session_dir.relative_to(wr)
        except ValueError:
            return {
                "status": "rejected",
                "report": {},
                "errors": [
                    {
                        "code": "E_SESSION_PATH",
                        "message": "scheme_session_dir must be inside workspace_root for default output, or pass output_subdir explicitly",
                        "details": {
                            "scheme_session_dir": str(session_dir),
                            "workspace_root": str(wr),
                        },
                    }
                ],
            }
        base = rel_session / "project" / "execution_prep"
        target_root = base / ts if use_ts else base

    def _fp(content: str) -> str:
        h = hashlib.sha256()
        h.update(content.encode("utf-8"))
        return h.hexdigest()

    copied: list[str] = []
    artifacts: list[dict[str, Any]] = []
    for name in REQUIRED_ARTIFACTS:
        content = (artifacts_dir / name).read_text(encoding="utf-8", errors="replace")
        rel = str(target_root / "scheme" / name)
        out = adapter.execute(ToolRequest(tool="workspace_write", arguments={"path": rel, "content": content}))
        if out.get("status") != "success":
            return out
        copied.append(rel)
        artifacts.append(
            {
                "type": "execution_prep_file",
                "path": rel,
                "fingerprint": _fp(content),
                "summary": f"copied scheme artifact: {name}",
            }
        )

    matrix_path = artifacts_dir / "experiment_matrix.json"
    if matrix_path.is_file():
        content = matrix_path.read_text(encoding="utf-8", errors="replace")
        rel = str(target_root / "scheme" / "experiment_matrix.json")
        out = adapter.execute(
            ToolRequest(
                tool="workspace_write",
                arguments={"path": rel, "content": content},
            )
        )
        if out.get("status") != "success":
            return out
        copied.append(rel)
        artifacts.append(
            {
                "type": "execution_prep_file",
                "path": rel,
                "fingerprint": _fp(content),
                "summary": "copied scheme artifact: experiment_matrix.json",
            }
        )

    checklist = _build_checklist(session_dir=session_dir, copied_files=copied)
    checklist_rel = str(target_root / "NEXT_STEPS.md")
    out = adapter.execute(ToolRequest(tool="workspace_write", arguments={"path": checklist_rel, "content": checklist}))
    if out.get("status") != "success":
        return out
    artifacts.append(
        {
            "type": "execution_prep_checklist",
            "path": checklist_rel,
            "fingerprint": _fp(checklist),
            "summary": "IDE next steps checklist",
        }
    )

    log = {
        "schema_version": "execution_prep_v1",
        "created_at": ts,
        "scheme_session_dir": str(session_dir),
        "copied_files": copied,
        "checklist_path": checklist_rel,
    }
    log_rel = str(target_root / "run_log.json")
    log_text = json.dumps(log, ensure_ascii=False, indent=2)
    out = adapter.execute(ToolRequest(tool="workspace_write", arguments={"path": log_rel, "content": log_text}))
    if out.get("status") != "success":
        return out
    artifacts.append(
        {
            "type": "execution_prep_log",
            "path": log_rel,
            "fingerprint": _fp(log_text),
            "summary": "execution prep run log",
        }
    )

    return {
        "status": "success",
        "report": {
            "target_root": str(target_root),
            "copied_files": copied,
            "checklist_path": checklist_rel,
            "run_log_path": log_rel,
        },
        "artifacts": artifacts,
    }


def _build_checklist(*, session_dir: Path, copied_files: list[str]) -> str:
    return "\n".join(
        [
            "# Execution Prep Checklist",
            "",
            f"- Source scheme session: `{session_dir}`",
            "- Review the copied scheme files under `scheme/` (mirror of `artifacts/`).",
            f"- Put **all code and experiment artifacts** under **`{session_dir / 'project'}`** (same session tree as `artifacts/`).",
            "- Suggested layout: `project/src/<package>/`, `project/scripts/`, run artifacts under `project/outputs/` (stable paths; no timestamp folders).",
            "- Implement per `architecture_draft.md` and `experiment_design.md`.",
            "- Run one initial dry run in IDE and record notes.",
            "- Update pass/fail outcomes after first experiment run.",
            "",
            "## Copied files",
            *[f"- `{p}`" for p in copied_files],
        ]
    )

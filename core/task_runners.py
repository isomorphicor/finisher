"""
Single entry for research/scheme tasks.

Scheme design: scripts/run_scheme_agent.py. IDE execution: mode ide_execution_agent
(core/ide_agent.py) runs an LLM with LocalIDEAdapter tools (read/write repo, allowlisted shell).
"""
from __future__ import annotations

from typing import Any


def run_research_task(task: dict[str, Any]) -> dict[str, Any]:
    """
    Run one task. task: request, mode, project?, session?
    Supported modes: design_only, scheme_agent, execution_prep, ide_execution_agent.
    """
    mode = (task.get("mode") or "design_only").strip()
    if mode == "design_only":
        return _run_design_only(task)
    if mode == "scheme_agent":
        return _run_scheme_agent(task)
    if mode == "execution_prep":
        return _run_execution_prep(task)
    if mode == "ide_execution_agent":
        return _run_ide_execution_agent(task)
    # Default: design_only
    return _run_design_only(task)


def _run_design_only(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "design_only",
        "message": "Contracts and runtime design live under docs/. For scheme design, use mode=scheme_agent (autonomous tool-skill agent).",
        "request": task.get("request", ""),
    }


def _run_scheme_agent(task: dict[str, Any]) -> dict[str, Any]:
    from core.scheme_agent import get_scheme_phase_default_agent_model, run_scheme_agent

    request = (task.get("request") or "").strip()
    model = (task.get("model") or "").strip() or None
    output_lang = (task.get("lang") or "").strip() or "en"
    return run_scheme_agent(
        task=request,
        model=model or get_scheme_phase_default_agent_model(),
        output_lang=output_lang,
        design_lang="en",
        allow_ideate=bool(task.get("allow_ideate", False)),
        verbose=bool(task.get("verbose", True)),
    )


def _run_execution_prep(task: dict[str, Any]) -> dict[str, Any]:
    from pathlib import Path

    from core.execution_prep import prepare_execution_workspace

    session_dir = str(task.get("scheme_session_dir") or "").strip()
    if not session_dir:
        return {
            "status": "rejected",
            "report": {},
            "errors": [{"code": "E_INPUT", "message": "scheme_session_dir is required for execution_prep mode", "details": {}}],
        }
    workspace_root = str(task.get("workspace_root") or ".").strip() or "."
    raw_osd = task.get("output_subdir")
    if raw_osd is None or (isinstance(raw_osd, str) and not raw_osd.strip()):
        output_subdir = None
    else:
        output_subdir = str(raw_osd).strip()
    return prepare_execution_workspace(
        scheme_session_dir=Path(session_dir),
        workspace_root=Path(workspace_root),
        output_subdir=output_subdir,
    )


def _tri_state_bool(task: dict[str, Any], key: str) -> bool | None:
    """Match ``run_ide_execution_agent`` optional flags: absent key → None (env may apply); explicit bool."""
    if key not in task:
        return None
    v = task[key]
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(int(v))
    s = str(v).strip().lower()
    if s in ("", "none", "null", "default"):
        return None
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off"):
        return False
    return None


def _run_ide_execution_agent(task: dict[str, Any]) -> dict[str, Any]:
    from pathlib import Path

    from core.execution_agent import run_ide_execution_agent

    session_dir = str(task.get("scheme_session_dir") or "").strip()
    if not session_dir:
        return {
            "status": "rejected",
            "report": {},
            "errors": [{"code": "E_INPUT", "message": "scheme_session_dir is required for ide_execution_agent mode", "details": {}}],
        }
    request = str(task.get("request") or task.get("task") or "").strip()
    workspace_root = str(task.get("workspace_root") or ".").strip() or "."
    model = (task.get("model") or "").strip() or None
    max_rounds = int(task.get("max_rounds") or 120)
    verbose = bool(task.get("verbose", True))
    tm = str(task.get("task_mode") or "override").strip().lower()
    if tm not in ("override", "supplement"):
        tm = "override"
    return run_ide_execution_agent(
        task=request,
        task_mode=tm,
        scheme_session_dir=Path(session_dir),
        workspace_root=Path(workspace_root),
        model=model,
        max_rounds=max_rounds,
        verbose=verbose,
        iteration_mode=_tri_state_bool(task, "iteration_mode"),
        exploration_mode=_tri_state_bool(task, "exploration_mode"),
    )

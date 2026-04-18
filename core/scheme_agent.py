"""
Autonomous scheme agent (tool skills + gates + optional JSON summaries).

Implementation is split across ``core/scheme_*.py`` modules; this file re-exports the
stable public API so imports like ``from core.scheme_agent import run_scheme_agent`` keep working.
"""
from __future__ import annotations

from core.ide_execution_config import (
    get_ide_execution_coder_model,
    get_ide_execution_int,
    get_ide_execution_skills_mode,
    get_ide_execution_translate_task_enabled,
    resolve_ide_execution_model,
    resolve_ide_execution_task_translate_model,
)
from core.scheme_agent_run import (
    review_scheme_package,
    revise_scheme_session,
    run_scheme_agent,
)
from core.scheme_gates import _section_gate
from core.scheme_paths import (
    PROJECTS_ROOT,
    REPO_ROOT,
    WORKSPACE_ROOT,
    get_default_new_session_name,
    get_default_scheme_project_name,
    warn_if_implicit_default_project_with_session,
)
from core.scheme_phase_models import get_scheme_phase_default_agent_model

__all__ = [
    "PROJECTS_ROOT",
    "REPO_ROOT",
    "WORKSPACE_ROOT",
    "get_default_new_session_name",
    "get_default_scheme_project_name",
    "get_ide_execution_coder_model",
    "get_ide_execution_int",
    "get_ide_execution_skills_mode",
    "get_ide_execution_translate_task_enabled",
    "get_scheme_phase_default_agent_model",
    "resolve_ide_execution_model",
    "resolve_ide_execution_task_translate_model",
    "review_scheme_package",
    "revise_scheme_session",
    "run_scheme_agent",
    "warn_if_implicit_default_project_with_session",
    "_section_gate",
]

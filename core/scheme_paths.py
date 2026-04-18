"""Project/session directory layout under the scheme runs root (see ``INVERST_SCHEME_PHASE_RUNS``).

Layout: ``<runs_root>/<project>/<session>/`` — ``--project`` and ``--session`` map to the two path
segments (e.g. ``…/algo_alpha/main/``). No ``projects/`` or ``sessions/`` wrapper dirs.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

REPO_ROOT = Path(__file__).resolve().parent.parent


def resolve_scheme_phase_runs_root() -> Path:
    """Where scheme sessions live: ``<root>/<project>/<session>/``.

    Priority:

    1. Environment ``INVERST_SCHEME_PHASE_RUNS`` (if set).
    2. ``config/settings.yaml`` → ``paths.runs_dir`` (absolute path or relative to repo root).
    3. ``<repo>/out/``.

    When (2) or (3) is used, sets ``INVERST_SCHEME_PHASE_RUNS`` in the environment so other code
    and subprocesses see the same root.
    """
    env = (os.environ.get("INVERST_SCHEME_PHASE_RUNS") or "").strip()
    if env:
        return Path(env).expanduser().resolve()

    from core.config import settings

    rd = (settings.paths.runs_dir or "").strip()
    if rd:
        p = Path(rd).expanduser()
        resolved = p.resolve() if p.is_absolute() else (REPO_ROOT / p).resolve()
        os.environ["INVERST_SCHEME_PHASE_RUNS"] = str(resolved)
        return resolved

    fallback = (REPO_ROOT / "out").resolve()
    os.environ["INVERST_SCHEME_PHASE_RUNS"] = str(fallback)
    return fallback


WORKSPACE_ROOT = resolve_scheme_phase_runs_root()
# Project folders live directly under the runs root; each session is ``<project>/<session>/``.
PROJECTS_ROOT = WORKSPACE_ROOT


def resolve_default_workspace_root() -> Path:
    """Default workspace for execution prep / IDE when ``--workspace-root`` is omitted on the CLI.

    Order:

    1. ``config/settings.yaml`` → ``paths.workspace_root`` (absolute or relative to the repo root).
    2. Parent of resolved ``paths.runs_dir`` when set (sessions often live under ``…/runs_root`` while
       code and data share a broader tree, e.g. ``…/Project``).
    3. ``REPO_ROOT``.
    """
    from core.config import settings

    ws = (settings.paths.workspace_root or "").strip()
    if ws:
        p = Path(ws).expanduser()
        return p.resolve() if p.is_absolute() else (REPO_ROOT / p).resolve()

    rd = (settings.paths.runs_dir or "").strip()
    if rd:
        rp = Path(rd).expanduser()
        resolved_runs = rp.resolve() if rp.is_absolute() else (REPO_ROOT / rp).resolve()
        parent = resolved_runs.parent
        if parent != resolved_runs:
            return parent
    return REPO_ROOT.resolve()


def resolve_workspace_root_cli_arg(raw: str | None) -> Path:
    """Resolve CLI ``--workspace-root``: empty or whitespace → :func:`resolve_default_workspace_root`."""
    if not (raw or "").strip():
        return resolve_default_workspace_root()
    return Path(str(raw).strip()).expanduser().resolve()


def resolve_workspace_root_for_scheme_session(
    *,
    scheme_session_dir: Path,
    requested_workspace_root: Path,
    repo_root: Path | None = None,
) -> tuple[Path, str | None]:
    """Return a workspace root that contains ``scheme_session_dir`` for execution prep and IDE tools.

    ``--workspace-root`` defaults from config (see :func:`resolve_default_workspace_root`) or may be
    set explicitly (e.g. repo checkout). When sessions live under
    ``paths.runs_dir`` outside that repo, ``prepare_execution_workspace`` would otherwise raise
    ``E_SESSION_PATH``. Resolution order:

    1. If ``requested_workspace_root`` already contains the session directory → use it.
    2. Else the common path of the repo and the session (e.g. ``…/Project`` for ``…/Project/finish``
       and ``…/Project/projects_generated/…/``).
    3. Else the scheme runs root (``WORKSPACE_ROOT``) if the session lies under it.
    4. Else the session directory's parent (always valid for ``relative_to``).
    """
    sd = scheme_session_dir.resolve()
    rw = requested_workspace_root.resolve()
    rr = (repo_root or REPO_ROOT).resolve()
    if sd.is_relative_to(rw):
        return rw, None
    try:
        common = Path(os.path.commonpath([str(rr), str(sd)]))
        if common != Path("/") and sd.is_relative_to(common) and rr.is_relative_to(common):
            return common, (
                f"workspace root set to {common} (repo + session share this prefix; "
                f"{rw} does not contain the session)"
            )
    except ValueError:
        pass
    rsr = WORKSPACE_ROOT.resolve()
    if sd.is_relative_to(rsr):
        return rsr, (
            f"workspace root set to scheme runs root {rsr} ({rw} does not contain the session)"
        )
    parent = sd.parent
    return parent, (
        f"workspace root set to session parent {parent} ({rw} does not contain the session)"
    )


def get_default_scheme_project_name() -> str:
    """Default for CLI ``--project`` when omitted.

    Set ``INVERST_DEFAULT_SCHEME_PROJECT`` (e.g. ``algo_alpha``) so runs land under
    ``<runs_root>/<name>/`` without repeating ``--project`` on every command.
    """
    raw = (os.environ.get("INVERST_DEFAULT_SCHEME_PROJECT") or "").strip()
    return raw if raw else "default"


def get_default_new_session_name() -> str:
    """Folder name when starting a new session without ``--session`` / ``--resume-latest``.

    Default ``main`` → e.g. ``…/algo_alpha/main/``. Set ``INVERST_DEFAULT_SCHEME_SESSION``
    to another name, or to ``timestamp`` / ``utc`` for a UTC ``%Y%m%dT%H%M%SZ`` folder.
    """
    raw = (os.environ.get("INVERST_DEFAULT_SCHEME_SESSION") or "main").strip()
    if raw.lower() in ("timestamp", "utc", "auto"):
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return _sanitize_project_name(raw) or "main"


def warn_if_implicit_default_project_with_session(
    *,
    project_name: str,
    session_name: str | None,
    stream: TextIO,
) -> None:
    """If user set ``--session`` but left project as the implicit ``default``, stderr hint."""
    if not (session_name or "").strip():
        return
    if (project_name or "").strip() != "default":
        return
    if (os.environ.get("INVERST_DEFAULT_SCHEME_PROJECT") or "").strip():
        return
    sid = str(session_name).strip()
    print(
        "[scheme] Note: paths are <runs_root>/<--project>/<--session>/. "
        f"Using project 'default' → …/default/{sid}/. "
        "Pass --project algo_alpha (or export INVERST_DEFAULT_SCHEME_PROJECT=algo_alpha) "
        "for …/algo_alpha/<session>/...",
        file=stream,
        flush=True,
    )


def ensure_scheme_session_dir(
    *,
    project_name: str = "default",
    session_name: str | None = None,
    resume_latest: bool = False,
) -> Path:
    """Ensure ``<runs_root>/<project>/<session>/`` exists with ``artifacts/`` and ``project/``.

    Same layout as the scheme agent session root (see ``_run_dir``). Use before an exploration-only
    IDE pass when no scheme run has created the session yet.
    """
    return _run_dir(project_name=project_name, session_name=session_name, resume_latest=resume_latest)


def _sanitize_project_name(raw: str) -> str:
    s = (raw or "").strip().lower()
    s = re.sub(r"[^a-z0-9._-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "default"


def _run_dir(*, project_name: str = "default", session_name: str | None = None, resume_latest: bool = False) -> Path:
    project = _sanitize_project_name(project_name)
    project_root = PROJECTS_ROOT / project
    project_root.mkdir(parents=True, exist_ok=True)

    if session_name and str(session_name).strip():
        sid = _sanitize_project_name(str(session_name))
        root = project_root / sid
    elif resume_latest and (project_root / "LATEST").is_file():
        sid = (project_root / "LATEST").read_text(encoding="utf-8", errors="replace").strip()
        root = project_root / sid if sid else (project_root / get_default_new_session_name())
    else:
        sid = get_default_new_session_name()
        root = project_root / sid

    root.mkdir(parents=True, exist_ok=True)
    (root / "artifacts").mkdir(exist_ok=True)
    (root / "project").mkdir(exist_ok=True)
    (project_root / "LATEST").write_text(root.name, encoding="utf-8")
    (root / "artifacts" / "session_meta.json").write_text(
        json.dumps(
            {
                "schema_version": "session_meta_v1",
                "project": project,
                "session_id": root.name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "active",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return root

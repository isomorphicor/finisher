from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.execution_prep import prepare_execution_workspace
from core.scheme_agent import get_default_scheme_project_name
from core.scheme_paths import WORKSPACE_ROOT, _sanitize_project_name


def _resolve_scheme_session_dir(
    *,
    scheme_session_dir: str | None,
    project: str,
    session: str | None,
    resume_latest: bool,
) -> Path:
    if scheme_session_dir:
        return Path(scheme_session_dir).resolve()

    workspace_root = WORKSPACE_ROOT
    proj = _sanitize_project_name(project)

    sid = (session or "").strip()
    if not sid and resume_latest:
        latest_file = workspace_root / proj / "LATEST"
        if not latest_file.is_file():
            raise SystemExit(f"Cannot find latest session for project '{project}': {latest_file}")
        sid = latest_file.read_text(encoding="utf-8", errors="replace").strip()

    if not sid:
        raise SystemExit("Provide scheme_session_dir, or use --session / --resume-latest with --project.")
    sid_clean = _sanitize_project_name(sid)

    candidates = [
        workspace_root / proj / sid_clean,
        workspace_root / "projects" / proj / "sessions" / sid_clean,
        workspace_root / "scheme_phase" / "projects" / proj / "sessions" / sid_clean,
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0].resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare IDE execution workspace from a scheme session.")
    parser.add_argument("scheme_session_dir", nargs="?", help="Path to scheme session directory containing artifacts/")
    parser.add_argument(
        "--project",
        default=get_default_scheme_project_name(),
        help="Top-level folder under scheme runs root (env INVERST_SCHEME_PHASE_RUNS). Default: env INVERST_DEFAULT_SCHEME_PROJECT or 'default'",
    )
    parser.add_argument("--session", default="", help="Session folder name under <project>/ (…/<project>/<session>/)")
    parser.add_argument("--resume-latest", action="store_true", help="Use LATEST session under project")
    parser.add_argument("--workspace-root", default=".", help="Repository root (must contain the scheme session path for default output).")
    parser.add_argument(
        "--output-subdir",
        default="",
        help="Optional. Subdir under workspace root for prep output (legacy). If omitted, writes to "
        "<session>/project/execution_prep/ (INVERST_EXECUTION_PREP_TIMESTAMP=1 for a UTC subfolder).",
    )
    args = parser.parse_args()

    session_dir = _resolve_scheme_session_dir(
        scheme_session_dir=args.scheme_session_dir,
        project=args.project,
        session=args.session,
        resume_latest=bool(args.resume_latest),
    )

    osd = (args.output_subdir or "").strip() or None
    result = prepare_execution_workspace(
        scheme_session_dir=session_dir,
        workspace_root=Path(args.workspace_root),
        output_subdir=osd,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

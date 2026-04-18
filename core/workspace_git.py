"""Optional git helpers for scheme session directories (preflight branch / clean / commit)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def _git_top_level(path: Path) -> Path | None:
    path = path.resolve()
    try:
        cp = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if int(cp.returncode) != 0:
            return None
        root = (cp.stdout or "").strip()
        return Path(root).resolve() if root else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def checkout_workspace_branch(*, session_dir: Path, branch: str) -> dict[str, Any]:
    """Create/switch branch at the git root containing ``session_dir`` (if any)."""
    session_dir = session_dir.resolve()
    b = (branch or "").strip()
    if not b:
        return {"status": "skipped", "reason": "empty_branch"}
    top = _git_top_level(session_dir)
    if top is None:
        return {"status": "skipped", "reason": "not_a_git_repository", "session_dir": str(session_dir)}
    try:
        cp = subprocess.run(
            ["git", "-C", str(top), "checkout", "-B", b],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "status": "ok" if int(cp.returncode) == 0 else "failed",
            "branch": b,
            "git_toplevel": str(top),
            "exit_code": int(cp.returncode),
            "stderr_tail": (cp.stderr or "")[-800:],
        }
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"status": "error", "branch": b, "git_toplevel": str(top), "error": str(e)}


def ensure_workspace_clean(*, session_dir: Path) -> dict[str, Any]:
    """Return ``clean`` if working tree has no unstaged/uncommitted changes (porcelain empty)."""
    session_dir = session_dir.resolve()
    top = _git_top_level(session_dir)
    if top is None:
        return {"status": "clean", "reason": "not_a_git_repository"}
    try:
        cp = subprocess.run(
            ["git", "-C", str(top), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if int(cp.returncode) != 0:
            return {"status": "unknown", "reason": "git_status_failed", "stderr_tail": (cp.stderr or "")[-400:]}
        dirty = bool((cp.stdout or "").strip())
        return {"status": "dirty" if dirty else "clean", "git_toplevel": str(top)}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"status": "unknown", "error": str(e)}


def commit_workspace_changes(*, session_dir: Path, message: str) -> dict[str, Any]:
    """``git add -A`` + ``git commit`` at the git root containing ``session_dir``."""
    session_dir = session_dir.resolve()
    msg = (message or "").strip() or "autonomy workspace commit"
    top = _git_top_level(session_dir)
    if top is None:
        return {"status": "skipped", "reason": "not_a_git_repository"}
    try:
        add = subprocess.run(
            ["git", "-C", str(top), "add", "-A"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if int(add.returncode) != 0:
            return {
                "status": "failed",
                "stage": "add",
                "exit_code": int(add.returncode),
                "stderr_tail": (add.stderr or "")[-800:],
            }
        cp = subprocess.run(
            ["git", "-C", str(top), "commit", "-m", msg],
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = (cp.stdout or "") + "\n" + (cp.stderr or "")
        # nothing to commit is exit 1 with typical message
        if int(cp.returncode) != 0 and "nothing to commit" in out.lower():
            return {"status": "noop", "reason": "nothing_to_commit", "git_toplevel": str(top)}
        return {
            "status": "ok" if int(cp.returncode) == 0 else "failed",
            "git_toplevel": str(top),
            "exit_code": int(cp.returncode),
            "stderr_tail": (cp.stderr or "")[-800:],
        }
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"status": "error", "error": str(e)}

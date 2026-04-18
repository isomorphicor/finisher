"""
IDE-facing tools for the execution agent: read/write repo files and run allowlisted shell commands.

These wrap runtime.adapters.LocalIDEAdapter (same surface as a local IDE tool bridge).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from core.scheme_paths import REPO_ROOT
from core.skill import BaseSkill
from runtime.tool_runtime import ToolRequest, ToolRuntime


def _normalize_rel(path: str) -> str:
    return (path or "").strip().lstrip("/")


def _under_allowed(rel: str, allowed_prefixes: tuple[str, ...]) -> bool:
    rel = _normalize_rel(rel)
    if not rel:
        return False
    for p in allowed_prefixes:
        p = p.strip().rstrip("/")
        if p in ("", "."):
            return True
        if rel == p or rel.startswith(p + "/"):
            return True
    return False


class IDEWorkspaceReadSkill(BaseSkill):
    name = "workspace_read"
    description = (
        "Read a UTF-8 text file under the workspace. "
        "`path` is relative to the repository root — must match exactly (copy/paste); wrong segments cause rejection. "
        "Session **scheme** files live under `.../<project>/<session>/artifacts/*.md` and may be large; the runtime uses a higher size limit for those paths."
    )

    def __init__(self, runtime: ToolRuntime):
        self._rt = runtime

    def get_parameters_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}

    def execute(self, **kwargs) -> dict[str, Any]:
        return self._rt.execute(ToolRequest(tool="workspace_read", arguments={"path": str(kwargs.get("path") or "")}))


class IDEWorkspaceWriteSkill(BaseSkill):
    name = "workspace_write"
    description = (
        "Create or overwrite a UTF-8 text file under allowed prefixes only. "
        "Use this for implementation code and experiment logs."
    )

    def __init__(self, runtime: ToolRuntime, allowed_prefixes: tuple[str, ...]):
        self._rt = runtime
        self._allowed_prefixes = allowed_prefixes

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        }

    def execute(self, **kwargs) -> dict[str, Any]:
        path = _normalize_rel(str(kwargs.get("path") or ""))
        content = str(kwargs.get("content") or "")
        if not _under_allowed(path, self._allowed_prefixes):
            return {
                "status": "rejected",
                "report": {},
                "errors": [
                    {
                        "code": "E_PATH_NOT_ALLOWED",
                        "message": "write path not under allowed prefixes",
                        "details": {"path": path, "allowed_prefixes": list(self._allowed_prefixes)},
                    }
                ],
            }
        return self._rt.execute(ToolRequest(tool="workspace_write", arguments={"path": path, "content": content}))


class IDEWorkspaceListSkill(BaseSkill):
    name = "workspace_list"
    description = "List files in a directory under the workspace (`path` relative to repo root, default `.`)."

    def __init__(self, runtime: ToolRuntime):
        self._rt = runtime

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"path": {"type": "string", "default": "."}},
        }

    def execute(self, **kwargs) -> dict[str, Any]:
        return self._rt.execute(ToolRequest(tool="workspace_list", arguments={"path": str(kwargs.get("path") or ".")}))


class IDEWorkspaceGrepSkill(BaseSkill):
    name = "workspace_grep"
    description = (
        "Regex search (Python `re`) over text files under the workspace. Returns **line-numbered context** per hit — "
        "use to **locate** relevant chunks in `docs/reference/ide_execution_rules.md` or `docs/skills/` **before** "
        "`workspace_read` on a whole file, saving tokens. "
        "Example: path=`docs/reference`, pattern=`Backtest|portfolio|Sharpe`, glob=`*.md`."
    )

    def __init__(self, runtime: ToolRuntime):
        self._rt = runtime

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern (e.g. CPCV|C\\(N,k\\))"},
                "path": {"type": "string", "default": "docs", "description": "Directory relative to repo root"},
                "glob": {"type": "string", "default": "*.md", "description": "Glob under path (e.g. *.md, *.py)"},
                "ignore_case": {"type": "boolean", "default": False},
                "context_lines": {"type": "integer", "default": 2, "description": "Lines before/after each match"},
                "max_matches": {"type": "integer", "default": 32},
                "max_total_chars": {"type": "integer", "default": 14000},
            },
            "required": ["pattern"],
        }

    def execute(self, **kwargs) -> dict[str, Any]:
        args: dict[str, Any] = {"pattern": str(kwargs.get("pattern") or "").strip()}
        if kwargs.get("path") is not None:
            args["path"] = str(kwargs.get("path"))
        if kwargs.get("glob") is not None:
            args["glob"] = str(kwargs.get("glob"))
        if kwargs.get("ignore_case") is not None:
            args["ignore_case"] = bool(kwargs.get("ignore_case"))
        if kwargs.get("context_lines") is not None:
            args["context_lines"] = int(kwargs.get("context_lines"))
        if kwargs.get("max_matches") is not None:
            args["max_matches"] = int(kwargs.get("max_matches"))
        if kwargs.get("max_total_chars") is not None:
            args["max_total_chars"] = int(kwargs.get("max_total_chars"))
        return self._rt.execute(ToolRequest(tool="workspace_grep", arguments=args))


class IDETerminalRunSkill(BaseSkill):
    name = "terminal_run"
    description = (
        "Run one shell command. First token must be allowlisted (python, python3, pytest, ls, cd, …). "
        "Set working directory with **`cwd`** (repo-relative), not a leading `cd` command alone — "
        "e.g. cwd=`path/to/dir`, command=`python -c \"...\"`. Capture stdout/stderr in the tool result."
    )

    def __init__(self, runtime: ToolRuntime):
        self._rt = runtime

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string", "default": "."},
                "timeout_sec": {"type": "integer", "minimum": 1, "maximum": 3600},
            },
            "required": ["command"],
        }

    def execute(self, **kwargs) -> dict[str, Any]:
        args: dict[str, Any] = {"command": str(kwargs.get("command") or "").strip()}
        if kwargs.get("cwd"):
            args["cwd"] = str(kwargs.get("cwd"))
        if kwargs.get("timeout_sec") is not None:
            args["timeout_sec"] = int(kwargs.get("timeout_sec"))
        return self._rt.execute(ToolRequest(tool="terminal_run_allowlisted", arguments=args))


def get_ide_execution_tools(
    *,
    runtime: ToolRuntime,
    allowed_write_prefixes: tuple[str, ...],
) -> tuple[list[dict[str, Any]], dict[str, Callable[..., dict[str, Any]]]]:
    skills: list[BaseSkill] = [
        IDEWorkspaceReadSkill(runtime),
        IDEWorkspaceGrepSkill(runtime),
        IDEWorkspaceWriteSkill(runtime, allowed_write_prefixes),
        IDEWorkspaceListSkill(runtime),
        IDETerminalRunSkill(runtime),
    ]
    tools_spec = [s.to_tool_definition() for s in skills]
    tools_impl: dict[str, Callable[..., dict[str, Any]]] = {s.name: (lambda _s=s, **kw: _s.execute(**kw)) for s in skills}
    return tools_spec, tools_impl


def build_allowed_write_prefixes(
    *,
    workspace_root: Path,
    scheme_session_dir: Path,
    outputs_subdir: str = "outputs",
    write_scope: str = "project",
) -> tuple[str, ...]:
    """
    Allow writes for IDE execution based on ``write_scope``.

    ``project`` (default): ``<session>/project/**`` (code + run outputs)
    ``session``: ``<session>/**`` (artifacts + project tree)
    ``repo``: entire **Inverst** checkout — only when ``workspace_root`` equals ``REPO_ROOT``; if the
    workspace was expanded to a parent directory (sessions under ``paths.runs_dir``), ``repo`` is
    treated as ``project`` so writes do not land in a stray top-level ``project/`` next to ``finish``.

    For ``project`` scope we ensure:
    - ``project/src/``
    - ``project/<outputs_subdir>/`` (default ``outputs``)
    """
    wr = workspace_root.resolve()
    scheme_session_dir = scheme_session_dir.resolve()
    scope = (write_scope or "project").strip().lower()

    if scope == "repo":
        rr = REPO_ROOT.resolve()
        if wr == rr:
            return (".",)
        # workspace_root is e.g. …/Project while REPO_ROOT is …/Project/finish — "." would allow
        # ``project/src/…`` → …/Project/project/ instead of …/projects_generated/…/project/.
        scope = "project"
    if scope == "session":
        return (str(scheme_session_dir.relative_to(wr)).replace("\\", "/"),)

    project_root = (scheme_session_dir / "project").resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    sub = (outputs_subdir or "outputs").strip().strip("/").replace("\\", "/") or "outputs"
    (project_root / "src").mkdir(parents=True, exist_ok=True)
    (project_root / sub).mkdir(parents=True, exist_ok=True)

    rel = str(project_root.relative_to(wr)).replace("\\", "/")
    return (rel,)

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from core.experiment_utils import read_file_under_run, write_file_under_run
from core.paper_search import format_papers_for_prompt, search_papers_multi_source
from core.skill import BaseSkill


def _normalize_path(path: str) -> str:
    p = (path or "").strip()
    if p.startswith("project/") or p.startswith("artifacts/"):
        return p
    return "artifacts/" + p.lstrip("/")


class RunReadFileSkill(BaseSkill):
    name = "read_file"
    description = "Read a file under the scheme run directory (project/ or artifacts/)."

    def __init__(self, run_root: Path):
        self._run_root = run_root.resolve()

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        }

    def execute(self, **kwargs) -> dict[str, Any]:
        path = str(kwargs.get("path") or "")
        out = read_file_under_run(self._run_root, path)
        if "error" in out:
            return {"status": "rejected", "report": {}, "errors": [{"code": "E_PATH", "message": out["error"], "details": {"path": path}}]}
        return {"status": "success", "report": {"path": _normalize_path(path), "content": out.get("content", "")}}


class RunWriteFileSkill(BaseSkill):
    name = "write_file"
    description = "Write a file under the scheme run directory (project/ or artifacts/)."

    def __init__(self, run_root: Path, allowed_write_paths: set[str] | frozenset[str] | None = None):
        self._run_root = run_root.resolve()
        self._allowed_write_paths = set(allowed_write_paths) if allowed_write_paths is not None else None

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        }

    def execute(self, **kwargs) -> dict[str, Any]:
        path = str(kwargs.get("path") or "")
        content = str(kwargs.get("content") or "")
        normalized = _normalize_path(path)
        if self._allowed_write_paths is not None and normalized not in self._allowed_write_paths:
            return {
                "status": "rejected",
                "report": {},
                "errors": [
                    {
                        "code": "E_PATH_NOT_ALLOWED",
                        "message": "path not allowed",
                        "details": {"path": normalized, "allowed": sorted(self._allowed_write_paths)},
                    }
                ],
            }
        out = write_file_under_run(self._run_root, normalized, content)
        if "error" in out:
            return {"status": "rejected", "report": {}, "errors": [{"code": "E_WRITE", "message": out["error"], "details": {"path": normalized}}]}
        return {"status": "success", "report": {"ok": True, "path": out.get("path", normalized), "chars": len(content)}}


class RunListFilesSkill(BaseSkill):
    name = "list_files"
    description = "List files under artifacts/ or project/ in the scheme run directory."

    def __init__(self, run_root: Path):
        self._run_root = run_root.resolve()

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"subdir": {"type": "string", "enum": ["artifacts", "project"]}},
            "required": ["subdir"],
        }

    def execute(self, **kwargs) -> dict[str, Any]:
        subdir = str(kwargs.get("subdir") or "artifacts")
        if subdir not in ("artifacts", "project"):
            return {"status": "rejected", "report": {}, "errors": [{"code": "E_SUBDIR", "message": "invalid subdir", "details": {"subdir": subdir}}]}
        d = (self._run_root / subdir).resolve()
        if not d.is_dir():
            return {"status": "success", "report": {"subdir": subdir, "files": []}}
        files = sorted(p.name for p in d.iterdir() if p.is_file())
        return {"status": "success", "report": {"subdir": subdir, "files": files}}


class PaperSearchSkill(BaseSkill):
    name = "paper_search"
    description = "Search papers (Semantic Scholar + arXiv) and return a prompt-friendly formatted block."

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit_per_source": {"type": "integer", "minimum": 1, "maximum": 20, "default": 4},
                "include_abstract": {"type": "boolean", "default": True},
                "max_chars": {"type": "integer", "minimum": 1000, "maximum": 50000, "default": 20000},
            },
            "required": ["query"],
        }

    def execute(self, **kwargs) -> dict[str, Any]:
        query = str(kwargs.get("query") or "").strip()
        if not query:
            return {"status": "rejected", "report": {}, "errors": [{"code": "E_QUERY", "message": "empty query", "details": {}}]}
        limit_per_source = int(kwargs.get("limit_per_source") or 4)
        include_abstract = bool(kwargs.get("include_abstract", True))
        max_chars = int(kwargs.get("max_chars") or 20000)
        hits = search_papers_multi_source(query, limit_per_source=limit_per_source)
        text = format_papers_for_prompt(hits, max_chars=max_chars, include_abstract=include_abstract) if hits else ""
        return {
            "status": "success",
            "report": {"query": query, "hit_count": len(hits), "formatted": text},
        }


def get_scheme_phase_tools(
    run_root: Path,
    *,
    allowed_write_paths: set[str] | frozenset[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Callable[..., dict[str, Any]]]]:
    skills: list[BaseSkill] = [
        RunReadFileSkill(run_root),
        RunWriteFileSkill(run_root, allowed_write_paths=allowed_write_paths),
        RunListFilesSkill(run_root),
        PaperSearchSkill(),
    ]
    tools_spec = [s.to_tool_definition() for s in skills]
    tools_impl: dict[str, Callable[..., dict[str, Any]]] = {s.name: (lambda _s=s, **kw: _s.execute(**kw)) for s in skills}
    return tools_spec, tools_impl


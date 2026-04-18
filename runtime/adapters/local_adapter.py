from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from runtime.tool_runtime import ToolRequest, ToolRuntime


def _safe_join(root: Path, rel: str) -> Path | None:
    rel_path = (rel or "").strip().lstrip("/")
    candidate = (root / rel_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


class LocalIDEAdapter(ToolRuntime):
    def __init__(
        self,
        workspace_root: Path,
        *,
        allowlisted_commands: set[str] | frozenset[str] | None = None,
        default_timeout_sec: int = 120,
    ):
        self.workspace_root = workspace_root.resolve()
        self.allowlisted_commands = set(allowlisted_commands or {"python", "pytest", "ls", "pwd", "echo"})
        self.default_timeout_sec = max(1, int(default_timeout_sec))
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def execute(self, request: ToolRequest) -> dict[str, Any]:
        tool = (request.tool or "").strip()
        args = request.arguments or {}
        if tool == "workspace_read":
            return self._workspace_read(args)
        if tool == "workspace_write":
            return self._workspace_write(args)
        if tool == "workspace_list":
            return self._workspace_list(args)
        if tool == "terminal_run_allowlisted":
            return self._terminal_run_allowlisted(args)
        if tool == "workspace_grep":
            return self._workspace_grep(args)
        return {"status": "rejected", "report": {}, "errors": [{"code": "E_TOOL", "message": f"unknown tool: {tool}", "details": {}}]}

    def _workspace_read(self, args: dict[str, Any]) -> dict[str, Any]:
        rel_path = str(args.get("path") or "")
        p = _safe_join(self.workspace_root, rel_path)
        if p is None or not p.is_file():
            return {"status": "rejected", "report": {}, "errors": [{"code": "E_PATH", "message": "invalid file path", "details": {"path": rel_path}}]}
        content = p.read_text(encoding="utf-8", errors="replace")
        return {"status": "success", "report": {"path": str(p.relative_to(self.workspace_root)), "content": content}}

    def _workspace_write(self, args: dict[str, Any]) -> dict[str, Any]:
        rel_path = str(args.get("path") or "")
        content = str(args.get("content") or "")
        p = _safe_join(self.workspace_root, rel_path)
        if p is None:
            return {"status": "rejected", "report": {}, "errors": [{"code": "E_PATH", "message": "invalid write path", "details": {"path": rel_path}}]}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"status": "success", "report": {"path": str(p.relative_to(self.workspace_root)), "chars": len(content)}}

    def _workspace_list(self, args: dict[str, Any]) -> dict[str, Any]:
        rel_path = str(args.get("path") or ".")
        p = _safe_join(self.workspace_root, rel_path)
        if p is None or not p.exists():
            return {"status": "rejected", "report": {}, "errors": [{"code": "E_PATH", "message": "invalid list path", "details": {"path": rel_path}}]}
        if p.is_file():
            return {"status": "success", "report": {"path": str(p.relative_to(self.workspace_root)), "entries": [str(p.name)]}}
        entries = sorted(str(x.relative_to(self.workspace_root)) for x in p.iterdir())
        return {"status": "success", "report": {"path": str(p.relative_to(self.workspace_root)), "entries": entries}}

    def _terminal_run_allowlisted(self, args: dict[str, Any]) -> dict[str, Any]:
        command = str(args.get("command") or "").strip()
        if not command:
            return {"status": "rejected", "report": {}, "errors": [{"code": "E_CMD", "message": "empty command", "details": {}}]}
        base = command.split()[0]
        if base not in self.allowlisted_commands:
            return {
                "status": "rejected",
                "report": {},
                "errors": [{"code": "E_CMD_NOT_ALLOWED", "message": "command not allowlisted", "details": {"command": base, "allowlisted": sorted(self.allowlisted_commands)}}],
            }
        timeout = int(args.get("timeout_sec") or self.default_timeout_sec)
        cwd_rel = str(args.get("cwd") or ".")
        cwd = _safe_join(self.workspace_root, cwd_rel)
        if cwd is None or not cwd.exists() or not cwd.is_dir():
            return {"status": "rejected", "report": {}, "errors": [{"code": "E_CWD", "message": "invalid cwd", "details": {"cwd": cwd_rel}}]}
        try:
            cp = subprocess.run(command, shell=True, cwd=str(cwd), capture_output=True, text=True, timeout=max(1, timeout))
        except subprocess.TimeoutExpired:
            return {"status": "rejected", "report": {}, "errors": [{"code": "E_TIMEOUT", "message": "command timed out", "details": {"command": command, "timeout_sec": timeout}}]}
        return {
            "status": "success",
            "report": {
                "command": command,
                "cwd": str(cwd.relative_to(self.workspace_root)),
                "exit_code": cp.returncode,
                "stdout": cp.stdout[-8000:],
                "stderr": cp.stderr[-8000:],
            },
        }

    def _workspace_grep(self, args: dict[str, Any]) -> dict[str, Any]:
        """Search text files under workspace for regex `pattern`; return matches with line context (for targeted rule/skill loading)."""
        raw_pat = str(args.get("pattern") or "").strip()
        if not raw_pat:
            return {
                "status": "rejected",
                "report": {},
                "errors": [{"code": "E_GREP", "message": "empty pattern", "details": {}}],
            }
        flags = re.IGNORECASE if bool(args.get("ignore_case")) else 0
        try:
            rx = re.compile(raw_pat, flags)
        except re.error as e:
            return {
                "status": "rejected",
                "report": {},
                "errors": [{"code": "E_GREP", "message": "invalid regex", "details": {"error": str(e)}}],
            }

        root_rel = str(args.get("path") or ".").strip()
        root = _safe_join(self.workspace_root, root_rel)
        if root is None or not root.exists():
            return {
                "status": "rejected",
                "report": {},
                "errors": [{"code": "E_PATH", "message": "invalid search root", "details": {"path": root_rel}}],
            }
        if not root.is_dir():
            return {
                "status": "rejected",
                "report": {},
                "errors": [{"code": "E_PATH", "message": "search path must be a directory", "details": {"path": root_rel}}],
            }

        glob_pat = str(args.get("glob") or "*.md").strip() or "*.md"
        max_matches = min(80, max(1, int(args.get("max_matches") or 32)))
        ctx_lines = max(0, min(8, int(args.get("context_lines") or 2)))
        max_file_bytes = min(2_000_000, max(10_000, int(args.get("max_file_bytes") or 600_000)))
        max_total_chars = min(100_000, max(2000, int(args.get("max_total_chars") or 14_000)))
        max_files_scan = min(2000, max(20, int(args.get("max_files") or 500)))

        matches: list[dict[str, Any]] = []
        chars_out = 0
        files_seen = 0
        truncated = False

        gp = glob_pat.strip() or "*.md"
        try:
            iterator = root.glob(gp) if "**" in gp else root.rglob(gp)
        except (ValueError, OSError):
            iterator = root.rglob("*.md")

        for p in iterator:
            if not p.is_file():
                continue
            files_seen += 1
            if files_seen > max_files_scan:
                truncated = True
                break
            try:
                sz = p.stat().st_size
            except OSError:
                continue
            if sz > max_file_bytes:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lines = text.splitlines()
            rel_file = str(p.relative_to(self.workspace_root)).replace("\\", "/")
            for i, line in enumerate(lines):
                if not rx.search(line):
                    continue
                lo = max(0, i - ctx_lines)
                hi = min(len(lines), i + ctx_lines + 1)
                block = "\n".join(f"{j + 1:5d}|{lines[j]}" for j in range(lo, hi))
                matches.append({"path": rel_file, "line": i + 1, "context": block})
                chars_out += len(rel_file) + len(block) + 40
                if len(matches) >= max_matches or chars_out >= max_total_chars:
                    truncated = True
                    break
            if truncated:
                break

        return {
            "status": "success",
            "report": {
                "pattern": raw_pat,
                "path": str(root.relative_to(self.workspace_root)).replace("\\", "/"),
                "glob": glob_pat,
                "truncated": truncated,
                "matches": matches,
                "hint": (
                    "Narrow `path` (e.g. docs/reference) or refine `pattern` if truncated. "
                    "Then workspace_read specific files; grep keeps token use low."
                    if truncated
                    else "Use hits to choose workspace_read targets; avoids loading whole trees."
                ),
            },
        }


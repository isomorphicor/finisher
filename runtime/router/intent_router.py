from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.tool_runtime import ToolRuntime
from skills.core.workspace_tools import WORKSPACE_TOOLS_SCHEMA, ensure_builtin_registry
from skills.registry_manager import SkillRegistry


CAPABILITY_TO_SKILL = {
    "workspace.read": "workspace_read",
    "workspace.write": "workspace_write",
    "workspace.list": "workspace_list",
    "terminal.run": "terminal_run_allowlisted",
}


class IntentRouter:
    def __init__(self, repo_root: Path, runtime: ToolRuntime):
        self.repo_root = repo_root.resolve()
        self.runtime = runtime
        ensure_builtin_registry(self.repo_root)
        self.registry = SkillRegistry(self.repo_root)

    def route(self, *, intent: str, arguments: dict[str, Any]) -> dict[str, Any]:
        skill_id = self._intent_to_skill(intent)
        if not skill_id:
            return {"status": "rejected", "report": {}, "errors": [{"code": "E_INTENT", "message": "unknown intent", "details": {"intent": intent}}]}
        err = _validate_required_fields(skill_id, arguments)
        if err:
            return err
        try:
            callable_skill, _entry = self.registry.load_callable(skill_id)
        except Exception as e:
            return {"status": "error", "report": {}, "errors": [{"code": "E_SKILL_LOAD", "message": str(e), "details": {"skill_id": skill_id}}]}
        out = callable_skill(self.runtime, **arguments)
        report = dict(out.get("report") or {})
        report["skill_id"] = skill_id
        report["intent"] = intent
        out["report"] = report
        return out

    def _intent_to_skill(self, intent: str) -> str | None:
        i = (intent or "").strip().lower()
        if i in CAPABILITY_TO_SKILL:
            return CAPABILITY_TO_SKILL[i]
        # lightweight keyword fallback
        if "read" in i:
            return "workspace_read"
        if "write" in i:
            return "workspace_write"
        if "list" in i or "ls" in i:
            return "workspace_list"
        if "terminal" in i or "command" in i or "run" in i:
            return "terminal_run_allowlisted"
        return None


def _validate_required_fields(skill_id: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
    schema = WORKSPACE_TOOLS_SCHEMA.get(skill_id) or {}
    required = schema.get("required") or []
    missing = [k for k in required if k not in arguments or arguments[k] in (None, "")]
    if missing:
        return {
            "status": "rejected",
            "report": {},
            "errors": [{"code": "E_SCHEMA", "message": "missing required arguments", "details": {"skill_id": skill_id, "missing": missing}}],
        }
    return None


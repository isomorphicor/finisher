from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.tool_runtime import ToolRequest, ToolRuntime


def workspace_read(runtime: ToolRuntime, **kwargs) -> dict[str, Any]:
    return runtime.execute(ToolRequest(tool="workspace_read", arguments=kwargs))


def workspace_write(runtime: ToolRuntime, **kwargs) -> dict[str, Any]:
    return runtime.execute(ToolRequest(tool="workspace_write", arguments=kwargs))


def workspace_list(runtime: ToolRuntime, **kwargs) -> dict[str, Any]:
    return runtime.execute(ToolRequest(tool="workspace_list", arguments=kwargs))


def terminal_run_allowlisted(runtime: ToolRuntime, **kwargs) -> dict[str, Any]:
    return runtime.execute(ToolRequest(tool="terminal_run_allowlisted", arguments=kwargs))


BUILTIN_SKILLS: list[dict[str, Any]] = [
    {
        "id": "workspace_read",
        "version": "0.1.0",
        "entry": "skills.core.workspace_tools:workspace_read",
        "capabilities": ["workspace.read"],
        "tags": ["io", "workspace"],
        "trust": "project",
    },
    {
        "id": "workspace_write",
        "version": "0.1.0",
        "entry": "skills.core.workspace_tools:workspace_write",
        "capabilities": ["workspace.write"],
        "tags": ["io", "workspace"],
        "trust": "project",
    },
    {
        "id": "workspace_list",
        "version": "0.1.0",
        "entry": "skills.core.workspace_tools:workspace_list",
        "capabilities": ["workspace.list"],
        "tags": ["io", "workspace"],
        "trust": "project",
    },
    {
        "id": "terminal_run_allowlisted",
        "version": "0.1.0",
        "entry": "skills.core.workspace_tools:terminal_run_allowlisted",
        "capabilities": ["terminal.run"],
        "tags": ["terminal"],
        "trust": "project",
    },
]


WORKSPACE_TOOLS_SCHEMA: dict[str, dict[str, Any]] = {
    "workspace_read": {"required": ["path"]},
    "workspace_write": {"required": ["path", "content"]},
    "workspace_list": {"required": ["path"]},
    "terminal_run_allowlisted": {"required": ["command"]},
}


def ensure_builtin_registry(repo_root: Path) -> None:
    from skills.registry_manager import SkillManifestEntry, SkillRegistry

    registry = SkillRegistry(repo_root)
    for item in BUILTIN_SKILLS:
        registry.upsert(SkillManifestEntry(**item))


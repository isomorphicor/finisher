from __future__ import annotations

from pathlib import Path

from runtime.adapters import LocalIDEAdapter, MCPAdapter
from runtime.tool_runtime import ToolRuntime


def build_runtime(
    *,
    workspace_root: Path,
    backend: str = "local",
    allowlisted_commands: set[str] | frozenset[str] | None = None,
    timeout_sec: int = 120,
) -> ToolRuntime:
    local = LocalIDEAdapter(
        workspace_root=workspace_root,
        allowlisted_commands=allowlisted_commands,
        default_timeout_sec=timeout_sec,
    )
    if backend == "mcp":
        return MCPAdapter(local)
    return local


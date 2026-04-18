from __future__ import annotations

from typing import Any

from runtime.adapters.local_adapter import LocalIDEAdapter
from runtime.tool_runtime import ToolRequest, ToolRuntime


class MCPAdapter(ToolRuntime):
    """
    MCP transport placeholder.
    For now it preserves the same interface and envelope while delegating to LocalIDEAdapter.
    """

    def __init__(self, fallback_local: LocalIDEAdapter):
        self._fallback_local = fallback_local

    def execute(self, request: ToolRequest) -> dict[str, Any]:
        out = self._fallback_local.execute(request)
        report = dict(out.get("report") or {})
        report["backend"] = "mcp_fallback_local"
        out["report"] = report
        return out


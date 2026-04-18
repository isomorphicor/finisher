from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolRequest:
    tool: str
    arguments: dict[str, Any]


class ToolRuntime(ABC):
    @abstractmethod
    def execute(self, request: ToolRequest) -> dict[str, Any]:
        """
        Execute one tool request and return the standard skill envelope:
        {status, report, artifacts?, errors?}.
        """
        raise NotImplementedError


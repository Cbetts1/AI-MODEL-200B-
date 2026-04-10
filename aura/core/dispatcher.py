"""aura/core/dispatcher.py — Routes a user message to the correct handler.

The Dispatcher inspects the incoming message and decides whether to:
  1. Call a registered Tool (if the message contains a tool-call directive).
  2. Delegate to a Workflow (if a multi-step workflow is requested).
  3. Pass straight through to the model for a standard chat reply.

At v0.1 the routing logic is intentionally simple (keyword-based).
In a future version this will be replaced by a proper function-calling loop
powered by the model itself.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .session import Session
    from ..tools.registry import ToolRegistry
    from ..workflows.base import Workflow


# ── simple intent detection ────────────────────────────────────────────────────

# Commands the user can type to trigger a tool directly:
#   /tool <tool_name> <args...>
_TOOL_PATTERN = re.compile(r"^/tool\s+(\w+)\s*(.*)", re.DOTALL)

# Workflow trigger:
#   /workflow <workflow_name> <args...>
_WORKFLOW_PATTERN = re.compile(r"^/workflow\s+(\w+)\s*(.*)", re.DOTALL)


class DispatchResult:
    """Carries the result of a dispatch decision."""

    def __init__(
        self,
        kind: str,              # "chat" | "tool" | "workflow"
        name: Optional[str] = None,
        args: Optional[str] = None,
    ) -> None:
        self.kind = kind
        self.name = name
        self.args = args

    def __repr__(self) -> str:
        return f"DispatchResult(kind={self.kind!r}, name={self.name!r})"


class Dispatcher:
    """Determines how to handle an incoming user message."""

    def __init__(
        self,
        tool_registry: "ToolRegistry",
    ) -> None:
        self.tool_registry = tool_registry

    def dispatch(self, message: str) -> DispatchResult:
        """Analyse *message* and return a DispatchResult.

        Priority order:
          1. Explicit /tool command
          2. Explicit /workflow command
          3. Default → chat
        """
        tool_match = _TOOL_PATTERN.match(message.strip())
        if tool_match:
            tool_name, args = tool_match.group(1), tool_match.group(2)
            return DispatchResult(kind="tool", name=tool_name, args=args)

        wf_match = _WORKFLOW_PATTERN.match(message.strip())
        if wf_match:
            wf_name, args = wf_match.group(1), wf_match.group(2)
            return DispatchResult(kind="workflow", name=wf_name, args=args)

        return DispatchResult(kind="chat")

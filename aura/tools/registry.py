"""aura/tools/registry.py — Tool registry and base Tool class.

The ToolRegistry is a dict-like container that stores Tool objects by name.
Tools can be registered via:
  - registry.register(my_tool)          — explicit registration
  - @registry.tool decorator            — decorator-style

The Dispatcher (core/dispatcher.py) calls registry.get(name) to look up tools,
and the CLI exposes `/tool list` to show all available tools.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class Tool(ABC):
    """Abstract base class for all AURA tools.

    Each tool has:
      name        : unique snake_case identifier used to call the tool.
      description : one-line human-readable summary shown in /tool list.
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    def run(self, args: str) -> str:
        """Execute the tool with the given argument string and return a result.

        Parameters
        ----------
        args:
            Raw argument string as typed by the user after the tool name.
            Tools parse this themselves (e.g. shlex.split).

        Returns
        -------
        str
            A human-readable result string.
        """


class ToolRegistry:
    """Stores and provides access to registered Tool instances."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Add a tool to the registry."""
        if not tool.name:
            raise ValueError("Tool must have a non-empty `name` attribute.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Return the tool with the given name, or None."""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """Return a sorted list of registered tool names."""
        return sorted(self._tools.keys())

    def summary(self) -> str:
        """Return a formatted summary table of all tools."""
        if not self._tools:
            return "No tools registered."
        lines = ["Available tools:", ""]
        for name in self.list_tools():
            tool = self._tools[name]
            lines.append(f"  {name:<20} — {tool.description}")
        return "\n".join(lines)

    # ── convenience decorator ──────────────────────────────────────────────────

    def tool(self, cls: type) -> type:
        """Class decorator: instantiate and register a Tool subclass."""
        instance = cls()
        self.register(instance)
        return cls


def build_default_registry() -> ToolRegistry:
    """Create a ToolRegistry pre-loaded with all built-in tools."""
    from .shell import ShellTool  # noqa: PLC0415
    from .file_ops import FileReadTool, FileWriteTool, FileListTool  # noqa: PLC0415
    from .web_search import WebSearchTool  # noqa: PLC0415
    from .apk_builder import ApkBuilderTool  # noqa: PLC0415

    registry = ToolRegistry()
    for tool in [
        ShellTool(),
        FileReadTool(),
        FileWriteTool(),
        FileListTool(),
        WebSearchTool(),
        ApkBuilderTool(),
    ]:
        registry.register(tool)
    return registry

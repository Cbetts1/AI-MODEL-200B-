"""aura/identity/persona.py — AURA's identity and persona.

The Persona class loads config/identity.yaml and exposes:
  - system_prompt()  : the system message injected at the start of every session.
  - name             : AURA's display name.
  - tone             : communication style (e.g. "concise", "friendly").
  - backstory        : short narrative about who AURA is.
  - mission          : AURA's driving purpose (help millions, change lives).

This keeps personality separate from code — change AURA's voice by editing
identity.yaml, not Python.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml


class Persona:
    """Encapsulates AURA's identity loaded from a YAML file."""

    def __init__(
        self,
        name: str = "AURA",
        tone: str = "concise, helpful, and direct",
        backstory: str = "",
        mission: str = "",
        capabilities: Optional[list] = None,
        custom_instructions: str = "",
    ) -> None:
        self.name = name
        self.tone = tone
        self.backstory = backstory
        self.mission = mission
        self.capabilities = capabilities or []
        self.custom_instructions = custom_instructions

    @classmethod
    def from_config(cls, config_path: str = "config/identity.yaml") -> "Persona":
        """Load persona from a YAML file."""
        path = Path(config_path)
        if not path.exists():
            # Return a sensible default if the file doesn't exist yet.
            return cls()
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(
            name=data.get("name", "AURA"),
            tone=data.get("tone", "concise, helpful, and direct"),
            backstory=data.get("backstory", ""),
            mission=data.get("mission", ""),
            capabilities=data.get("capabilities", []),
            custom_instructions=data.get("custom_instructions", ""),
        )

    def system_prompt(self) -> str:
        """Build the system prompt that seeds every new conversation."""
        parts = [
            f"You are {self.name}, an AI Unified Reasoning Architecture.",
            f"Your communication style is: {self.tone}.",
        ]
        if self.mission:
            parts.append(f"Your mission: {self.mission}")
        if self.backstory:
            parts.append(self.backstory)
        if self.capabilities:
            caps = ", ".join(self.capabilities)
            parts.append(f"Your capabilities include: {caps}.")
        if self.custom_instructions:
            parts.append(self.custom_instructions)
        parts.append(
            "When the user asks you to use a tool, emit /tool <name> <args>. "
            "When a workflow is needed, emit /workflow <name> <args>."
        )
        return " ".join(parts)

    def __repr__(self) -> str:
        return f"<Persona name={self.name!r}>"

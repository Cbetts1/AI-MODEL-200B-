"""aura/core/session.py — Per-conversation session state.

A Session holds:
  - conversation_id : unique identifier for this conversation
  - history         : ordered list of {"role": "user"|"assistant", "content": str}
  - metadata        : arbitrary key/value store for user preferences, etc.

The session is intentionally plain Python — no ORM, no database required at v0.1.
Persistence is handled by AuraMemory (see memory.py).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Message:
    """A single turn in the conversation."""
    role: str       # "user" | "assistant" | "system" | "tool"
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class Session:
    """Holds the live state for one AURA conversation."""

    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    history: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── helpers ────────────────────────────────────────────────────────────────

    def add_message(self, role: str, content: str) -> Message:
        """Append a message and return it."""
        msg = Message(role=role, content=content)
        self.history.append(msg)
        return msg

    def get_history_dicts(self) -> List[Dict[str, str]]:
        """Return history as a list of plain dicts (compatible with OpenAI API)."""
        return [m.to_dict() for m in self.history]

    def clear(self) -> None:
        """Wipe conversation history (keeps metadata)."""
        self.history.clear()

    def __len__(self) -> int:
        return len(self.history)

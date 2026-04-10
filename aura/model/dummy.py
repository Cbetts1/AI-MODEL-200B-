"""aura/model/dummy.py — Echo (dummy) model backend for offline testing.

EchoModelBackend requires no external dependencies and no running server.
It simply echoes the last user message back, prefixed with "[echo]".

Usage (config/aura.yaml)
------------------------
    model:
      backend: echo
"""

from __future__ import annotations

from typing import List, Dict

from .base import ModelBackend


class EchoModelBackend(ModelBackend):
    """Offline echo backend — returns the last user message with a prefix.

    Useful for end-to-end testing of the CLI/engine pipeline without a live
    model server.
    """

    def is_available(self) -> bool:
        return True

    def complete(self, messages: List[Dict[str, str]]) -> str:
        """Return the last user message prefixed with '[echo] '."""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return f"[echo] {msg['content']}"
        return "[echo] (no user message found)"

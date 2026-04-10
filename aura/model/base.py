"""aura/model/base.py — Abstract base class for all model backends.

Every model backend (local or remote) must implement the `complete` method,
which takes a list of message dicts and returns the assistant's reply string.

This design means the rest of AURA never imports a specific backend directly —
it only depends on this interface.  Swapping models is therefore a one-line
config change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict


class ModelBackend(ABC):
    """Abstract interface for an LLM backend."""

    @abstractmethod
    def complete(self, messages: List[Dict[str, str]]) -> str:
        """Given a conversation history, return the next assistant message.

        Parameters
        ----------
        messages:
            OpenAI-style list of dicts, e.g.
            [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

        Returns
        -------
        str
            The assistant's reply text.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this backend is ready to serve requests."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

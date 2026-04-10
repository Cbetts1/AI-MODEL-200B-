"""aura/core/memory.py — Short-term and long-term memory for AURA.

Short-term memory  : the live Session object (in-process, fast).
Long-term memory   : JSON file on disk keyed by conversation_id.

Design notes
------------
- The file format is intentionally simple (newline-delimited JSON records) so
  it is readable, portable, and doesn't require a database.
- In a future version this layer can be swapped out for a vector store
  (e.g. Chroma, FAISS) without changing the rest of the engine.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Dict, Any

from .session import Session, Message


class AuraMemory:
    """Manages persistence of conversation sessions to disk."""

    DEFAULT_MEMORY_DIR = Path.home() / ".aura" / "memory"

    def __init__(self, memory_dir: str | Path | None = None) -> None:
        self.memory_dir = Path(memory_dir or self.DEFAULT_MEMORY_DIR)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    # ── private ────────────────────────────────────────────────────────────────

    def _session_path(self, session: Session) -> Path:
        return self.memory_dir / f"{session.conversation_id}.jsonl"

    # ── public API ─────────────────────────────────────────────────────────────

    def save(self, session: Session) -> None:
        """Persist the full session history to disk (overwrites previous save)."""
        path = self._session_path(session)
        with path.open("w", encoding="utf-8") as fh:
            for msg in session.history:
                fh.write(json.dumps(msg.to_dict()) + "\n")

    def load(self, session: Session) -> None:
        """Load history from disk into a session object (appends to existing)."""
        path = self._session_path(session)
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    record = json.loads(line)
                    session.history.append(Message(**record))

    def list_sessions(self) -> List[str]:
        """Return conversation IDs of all saved sessions."""
        return [p.stem for p in self.memory_dir.glob("*.jsonl")]

    def delete(self, conversation_id: str) -> bool:
        """Delete a saved session.  Returns True if it existed."""
        path = self.memory_dir / f"{conversation_id}.jsonl"
        if path.exists():
            path.unlink()
            return True
        return False

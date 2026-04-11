"""aura/storage/base.py — Abstract storage backend interface.

AURA v0.6.0 introduces a pluggable storage layer so that persistent data
(notes, memory, session history, self-build proposals) can be backed by
different engines depending on deployment scale:

  FileStore    — JSON files in ~/.aura/ (default, zero dependencies)
  SQLiteStore  — SQLite database for better query performance
  (future)     — PostgreSQL, Redis, S3, cloud KV stores…

All backends implement the same ``StorageBackend`` interface so switching
backends requires no changes to the rest of the codebase.

Usage
-----
    from aura.storage.file_store import FileStore
    store = FileStore()
    store.set("notes", "todo", "Buy milk")
    value = store.get("notes", "todo")    # "Buy milk"
    store.delete("notes", "todo")
    all_keys = store.list_keys("notes")   # ["todo"]
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class StorageBackend(ABC):
    """Abstract key-value store grouped by *namespace*.

    A namespace is a logical partition (e.g. ``"notes"``, ``"sessions"``).
    Within a namespace each entry has a string key and a JSON-serialisable
    value.
    """

    @abstractmethod
    def get(self, namespace: str, key: str) -> Optional[Any]:
        """Return the value stored at *namespace/key*, or ``None``."""

    @abstractmethod
    def set(self, namespace: str, key: str, value: Any) -> None:
        """Store *value* at *namespace/key* (upsert semantics)."""

    @abstractmethod
    def delete(self, namespace: str, key: str) -> bool:
        """Delete *namespace/key*.  Returns True if the key existed."""

    @abstractmethod
    def list_keys(self, namespace: str) -> List[str]:
        """Return all keys in *namespace* in sorted order."""

    @abstractmethod
    def all_items(self, namespace: str) -> Dict[str, Any]:
        """Return a dict of all key→value pairs in *namespace*."""

    def namespace_exists(self, namespace: str) -> bool:
        """Return True if *namespace* contains at least one key."""
        return bool(self.list_keys(namespace))

    def clear_namespace(self, namespace: str) -> int:
        """Delete all keys in *namespace*.  Returns number of keys deleted."""
        keys = self.list_keys(namespace)
        for key in keys:
            self.delete(namespace, key)
        return len(keys)

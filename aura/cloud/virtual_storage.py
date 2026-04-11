"""aura/cloud/virtual_storage.py — AURA Virtual Cloud Storage.

VirtualStorage wraps AURA's existing SQLiteStore backend and adds:

  • Namespaced partitions — each virtual server or service gets its own
    namespace so data is logically isolated.
  • Auto-expand — when a new namespace is first written to, the storage
    layer creates it automatically.
  • Usage tracking — per-namespace key counts and total size estimates.
  • Snapshot / restore — export/import all data for backup or migration.

The underlying engine is SQLite (zero extra dependencies, ships with Python).
All data is persisted to disk at ``~/.aura/cloud/cloud_storage.db``.

Usage
-----
    from aura.cloud.virtual_storage import VirtualStorage
    vs = VirtualStorage()
    vs.put("server-a", "config", {"workers": 4})
    print(vs.get("server-a", "config"))   # {"workers": 4}
    print(vs.namespaces())                # ["server-a"]
    print(vs.usage())                     # {"server-a": {"keys": 1, ...}}
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..storage.sqlite_store import SQLiteStore


_DEFAULT_DB = Path.home() / ".aura" / "cloud" / "cloud_storage.db"


class VirtualStorage:
    """Namespaced persistent storage for the virtual cloud layer.

    Parameters
    ----------
    db_path:
        Path to the SQLite file.  Defaults to ``~/.aura/cloud/cloud_storage.db``.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        path = db_path or _DEFAULT_DB
        path.parent.mkdir(parents=True, exist_ok=True)
        self._store = SQLiteStore(db_path=path)
        self._lock = threading.Lock()
        self._created_at: float = time.time()
        self._writes: int = 0
        self._reads: int = 0

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def get(self, namespace: str, key: str) -> Optional[Any]:
        """Return stored value, or None."""
        with self._lock:
            self._reads += 1
        return self._store.get(namespace, key)

    def put(self, namespace: str, key: str, value: Any) -> None:
        """Store *value* under *namespace/key* (upsert)."""
        with self._lock:
            self._writes += 1
        self._store.set(namespace, key, value)

    def delete(self, namespace: str, key: str) -> bool:
        """Delete *namespace/key*.  Returns True if it existed."""
        return self._store.delete(namespace, key)

    def keys(self, namespace: str) -> List[str]:
        """List all keys in *namespace*."""
        return self._store.list_keys(namespace)

    def all_items(self, namespace: str) -> Dict[str, Any]:
        """Return all key→value pairs in *namespace*."""
        return self._store.all_items(namespace)

    def clear_namespace(self, namespace: str) -> int:
        """Delete every key in *namespace*.  Returns number of keys removed."""
        return self._store.clear_namespace(namespace)

    # ── namespace management ───────────────────────────────────────────────────

    def namespaces(self) -> List[str]:
        """Return all known namespaces (those with at least one key)."""
        # Query the underlying sqlite store for distinct namespaces
        try:
            rows = self._store._conn.execute(
                "SELECT DISTINCT namespace FROM store ORDER BY namespace"
            ).fetchall()
            return [r[0] for r in rows]
        except Exception:  # noqa: BLE001
            return []

    # ── snapshot / restore ─────────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        """Export all data as a nested dict ``{namespace: {key: value}}``."""
        result: Dict[str, Dict[str, Any]] = {}
        for ns in self.namespaces():
            result[ns] = self._store.all_items(ns)
        return result

    def restore(self, data: Dict[str, Dict[str, Any]]) -> int:
        """Import data from a snapshot dict.  Returns total keys written."""
        total = 0
        for ns, items in data.items():
            for key, value in items.items():
                self._store.set(ns, key, value)
                total += 1
        return total

    # ── introspection ──────────────────────────────────────────────────────────

    def usage(self) -> Dict[str, Any]:
        """Return per-namespace usage statistics."""
        result: Dict[str, Any] = {}
        for ns in self.namespaces():
            keys = self._store.list_keys(ns)
            items = self._store.all_items(ns)
            # Rough size estimate: JSON encoding of all values
            size_bytes = sum(
                len(json.dumps(v, ensure_ascii=False).encode()) for v in items.values()
            )
            result[ns] = {"keys": len(keys), "size_bytes": size_bytes}
        return result

    def stats(self) -> Dict[str, Any]:
        """Return overall storage statistics."""
        namespaces = self.namespaces()
        total_keys = sum(len(self._store.list_keys(ns)) for ns in namespaces)
        with self._lock:
            return {
                "namespaces": len(namespaces),
                "total_keys": total_keys,
                "total_reads": self._reads,
                "total_writes": self._writes,
                "uptime_seconds": round(time.time() - self._created_at, 2),
            }

    def close(self) -> None:
        """Close the underlying database connection."""
        self._store.close()

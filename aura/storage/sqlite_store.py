"""aura/storage/sqlite_store.py — SQLite-backed storage backend.

A higher-performance alternative to ``FileStore`` that stores all namespaces
in a single SQLite database file.  Suitable for multi-namespace deployments
with thousands of keys.

The database schema is intentionally minimal:
  CREATE TABLE store (
      namespace TEXT NOT NULL,
      key       TEXT NOT NULL,
      value     TEXT NOT NULL,   -- JSON-encoded
      PRIMARY KEY (namespace, key)
  );

Usage
-----
    from aura.storage.sqlite_store import SQLiteStore
    store = SQLiteStore()
    store.set("sessions", "abc123", {"messages": []})
    print(store.get("sessions", "abc123"))

Dependencies
------------
Uses only the Python standard-library ``sqlite3`` module — no extra packages
required.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import StorageBackend

_DEFAULT_PATH = Path.home() / ".aura" / "storage" / "aura.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS store (
    namespace TEXT NOT NULL,
    key       TEXT NOT NULL,
    value     TEXT NOT NULL,
    PRIMARY KEY (namespace, key)
);
"""


class SQLiteStore(StorageBackend):
    """SQLite-backed key-value store.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.
        Defaults to ``~/.aura/storage/aura.db``.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._path = db_path or _DEFAULT_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    # ── StorageBackend implementation ──────────────────────────────────────────

    def get(self, namespace: str, key: str) -> Optional[Any]:
        row = self._conn.execute(
            "SELECT value FROM store WHERE namespace=? AND key=?",
            (namespace, key),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def set(self, namespace: str, key: str, value: Any) -> None:
        self._conn.execute(
            "INSERT INTO store (namespace, key, value) VALUES (?, ?, ?)"
            "  ON CONFLICT(namespace, key) DO UPDATE SET value=excluded.value",
            (namespace, key, json.dumps(value, ensure_ascii=False)),
        )
        self._conn.commit()

    def delete(self, namespace: str, key: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM store WHERE namespace=? AND key=?",
            (namespace, key),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def list_keys(self, namespace: str) -> List[str]:
        rows = self._conn.execute(
            "SELECT key FROM store WHERE namespace=? ORDER BY key",
            (namespace,),
        ).fetchall()
        return [r[0] for r in rows]

    def all_items(self, namespace: str) -> Dict[str, Any]:
        rows = self._conn.execute(
            "SELECT key, value FROM store WHERE namespace=? ORDER BY key",
            (namespace,),
        ).fetchall()
        return {r[0]: json.loads(r[1]) for r in rows}

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __del__(self) -> None:
        try:
            self._conn.close()
        except Exception:  # noqa: BLE001
            pass

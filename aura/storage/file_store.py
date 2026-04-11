"""aura/storage/file_store.py — JSON file-based storage backend.

The default storage backend for AURA.  Data is stored as JSON files inside
``~/.aura/storage/<namespace>.json`` — one file per namespace.

This backend is:
  • Zero-dependency (uses only the Python standard library)
  • Human-readable (plain JSON files, easy to inspect / backup)
  • Fast enough for single-user deployments

For multi-user or high-throughput deployments switch to ``SQLiteStore`` or
a future cloud-backed store — the interface is identical.

Usage
-----
    from aura.storage.file_store import FileStore
    store = FileStore()
    store.set("notes", "shopping", "Buy milk, eggs, bread")
    print(store.get("notes", "shopping"))
    store.delete("notes", "shopping")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import StorageBackend

_DEFAULT_DIR = Path.home() / ".aura" / "storage"


class FileStore(StorageBackend):
    """JSON-file-backed key-value store.

    Parameters
    ----------
    base_dir:
        Directory where namespace JSON files are stored.
        Defaults to ``~/.aura/storage/``.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._dir = base_dir or _DEFAULT_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    # ── StorageBackend implementation ──────────────────────────────────────────

    def get(self, namespace: str, key: str) -> Optional[Any]:
        data = self._load(namespace)
        return data.get(key)

    def set(self, namespace: str, key: str, value: Any) -> None:
        data = self._load(namespace)
        data[key] = value
        self._save(namespace, data)

    def delete(self, namespace: str, key: str) -> bool:
        data = self._load(namespace)
        if key not in data:
            return False
        del data[key]
        self._save(namespace, data)
        return True

    def list_keys(self, namespace: str) -> List[str]:
        data = self._load(namespace)
        return sorted(data.keys())

    def all_items(self, namespace: str) -> Dict[str, Any]:
        return dict(self._load(namespace))

    # ── private ────────────────────────────────────────────────────────────────

    def _path(self, namespace: str) -> Path:
        safe = namespace.replace("/", "_").replace("..", "")
        return self._dir / f"{safe}.json"

    def _load(self, namespace: str) -> Dict[str, Any]:
        path = self._path(namespace)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                return {}
        return {}

    def _save(self, namespace: str, data: Dict[str, Any]) -> None:
        self._path(namespace).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

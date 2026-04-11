"""tests/test_storage.py — Tests for aura.storage backends (AURA v0.6.0)."""

import pytest
from pathlib import Path

from aura.storage.file_store import FileStore
from aura.storage.sqlite_store import SQLiteStore
from aura.storage.base import StorageBackend


# ── parametrise over both backends ────────────────────────────────────────────

@pytest.fixture(params=["file", "sqlite"])
def store(request, tmp_path):
    if request.param == "file":
        yield FileStore(base_dir=tmp_path / "storage")
    else:
        db = SQLiteStore(db_path=tmp_path / "test.db")
        yield db
        db.close()


# Some tests need a fresh store per test — use autouse=False fixtures


@pytest.fixture()
def file_store(tmp_path):
    return FileStore(base_dir=tmp_path / "fs")


@pytest.fixture()
def sqlite_store(tmp_path):
    db = SQLiteStore(db_path=tmp_path / "test.db")
    yield db
    db.close()


# ── Interface tests (run against both backends via parametrised fixture) ───────

class TestStorageBackendInterface:
    def test_is_subclass_of_base(self, tmp_path):
        fs = FileStore(base_dir=tmp_path / "x")
        assert isinstance(fs, StorageBackend)

    def test_set_and_get(self, store):
        store.set("ns", "key1", "value1")
        assert store.get("ns", "key1") == "value1"

    def test_get_missing_returns_none(self, store):
        assert store.get("ns", "missing") is None

    def test_overwrite(self, store):
        store.set("ns", "k", "v1")
        store.set("ns", "k", "v2")
        assert store.get("ns", "k") == "v2"

    def test_delete_existing(self, store):
        store.set("ns", "del_key", "val")
        result = store.delete("ns", "del_key")
        assert result is True
        assert store.get("ns", "del_key") is None

    def test_delete_missing(self, store):
        result = store.delete("ns", "nonexistent")
        assert result is False

    def test_list_keys_empty(self, store):
        assert store.list_keys("empty_ns") == []

    def test_list_keys_sorted(self, store):
        store.set("ns", "zebra", 1)
        store.set("ns", "apple", 2)
        store.set("ns", "mango", 3)
        assert store.list_keys("ns") == ["apple", "mango", "zebra"]

    def test_all_items(self, store):
        store.set("items_ns", "a", 1)
        store.set("items_ns", "b", 2)
        items = store.all_items("items_ns")
        assert items == {"a": 1, "b": 2}

    def test_namespace_exists_true(self, store):
        store.set("exist_ns", "x", "y")
        assert store.namespace_exists("exist_ns") is True

    def test_namespace_exists_false(self, store):
        assert store.namespace_exists("phantom_ns") is False

    def test_clear_namespace(self, store):
        store.set("clr", "a", 1)
        store.set("clr", "b", 2)
        count = store.clear_namespace("clr")
        assert count == 2
        assert store.list_keys("clr") == []

    def test_multiple_namespaces_isolated(self, store):
        store.set("ns_a", "key", "val_a")
        store.set("ns_b", "key", "val_b")
        assert store.get("ns_a", "key") == "val_a"
        assert store.get("ns_b", "key") == "val_b"

    def test_json_serialisable_values(self, store):
        data = {"nested": {"list": [1, 2, 3], "flag": True}}
        store.set("json_ns", "obj", data)
        retrieved = store.get("json_ns", "obj")
        assert retrieved == data


# ── FileStore-specific ────────────────────────────────────────────────────────

class TestFileStore:
    def test_files_created_in_base_dir(self, tmp_path):
        base = tmp_path / "custom_store"
        fs = FileStore(base_dir=base)
        fs.set("mynotes", "hello", "world")
        assert (base / "mynotes.json").exists()

    def test_default_dir_used_when_none(self):
        # Just check it doesn't crash and has correct type
        from aura.storage.file_store import _DEFAULT_DIR
        assert isinstance(_DEFAULT_DIR, Path)

    def test_namespace_path_sanitises_slashes(self, tmp_path):
        fs = FileStore(base_dir=tmp_path / "fs2")
        # Should not raise and should not create subdirectories
        fs.set("a/b", "key", "val")
        assert fs.get("a/b", "key") == "val"

    def test_corrupted_file_returns_empty(self, tmp_path):
        base = tmp_path / "corrupt"
        base.mkdir()
        (base / "bad.json").write_text("NOT JSON {{{", encoding="utf-8")
        fs = FileStore(base_dir=base)
        assert fs.get("bad", "any") is None


# ── SQLiteStore-specific ──────────────────────────────────────────────────────

class TestSQLiteStore:
    def test_db_file_created(self, tmp_path):
        db_path = tmp_path / "test.db"
        db = SQLiteStore(db_path=db_path)
        db.set("x", "y", "z")
        db.close()
        assert db_path.exists()

    def test_data_persists_across_connections(self, tmp_path):
        db_path = tmp_path / "persist.db"
        db1 = SQLiteStore(db_path=db_path)
        db1.set("sessions", "abc", {"user": "alice"})
        db1.close()

        db2 = SQLiteStore(db_path=db_path)
        val = db2.get("sessions", "abc")
        db2.close()
        assert val == {"user": "alice"}

    def test_upsert_semantics(self, tmp_path):
        db = SQLiteStore(db_path=tmp_path / "upsert.db")
        db.set("ns", "k", "first")
        db.set("ns", "k", "second")
        assert db.get("ns", "k") == "second"
        db.close()

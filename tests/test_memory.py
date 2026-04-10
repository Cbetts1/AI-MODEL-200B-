"""tests/test_memory.py — Unit tests for aura.core.memory."""

import pytest
from pathlib import Path

from aura.core.session import Session
from aura.core.memory import AuraMemory


@pytest.fixture
def tmp_memory(tmp_path):
    """Return an AuraMemory instance using a temporary directory."""
    return AuraMemory(memory_dir=tmp_path)


class TestAuraMemory:
    def test_save_and_load(self, tmp_memory):
        session = Session()
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")
        tmp_memory.save(session)

        # Load into a fresh session with the same ID
        session2 = Session()
        session2.conversation_id = session.conversation_id
        tmp_memory.load(session2)

        assert len(session2) == 2
        assert session2.history[0].role == "user"
        assert session2.history[0].content == "Hello"

    def test_load_nonexistent(self, tmp_memory):
        """Loading a session that was never saved should silently do nothing."""
        session = Session()
        original_len = len(session)
        tmp_memory.load(session)  # should not raise
        assert len(session) == original_len

    def test_list_sessions(self, tmp_memory):
        s1, s2 = Session(), Session()
        s1.add_message("user", "a")
        s2.add_message("user", "b")
        tmp_memory.save(s1)
        tmp_memory.save(s2)
        ids = tmp_memory.list_sessions()
        assert s1.conversation_id in ids
        assert s2.conversation_id in ids

    def test_delete(self, tmp_memory):
        session = Session()
        session.add_message("user", "bye")
        tmp_memory.save(session)
        assert session.conversation_id in tmp_memory.list_sessions()

        result = tmp_memory.delete(session.conversation_id)
        assert result is True
        assert session.conversation_id not in tmp_memory.list_sessions()

    def test_delete_nonexistent(self, tmp_memory):
        assert tmp_memory.delete("nonexistent-id") is False

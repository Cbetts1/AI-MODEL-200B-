"""tests/test_session.py — Unit tests for aura.core.session."""

import pytest
from aura.core.session import Message, Session


class TestMessage:
    def test_to_dict(self):
        msg = Message(role="user", content="Hello")
        assert msg.to_dict() == {"role": "user", "content": "Hello"}

    def test_roles(self):
        for role in ("user", "assistant", "system", "tool"):
            msg = Message(role=role, content="test")
            assert msg.role == role


class TestSession:
    def test_default_id_is_unique(self):
        s1, s2 = Session(), Session()
        assert s1.conversation_id != s2.conversation_id

    def test_add_message(self):
        session = Session()
        msg = session.add_message("user", "hi")
        assert len(session) == 1
        assert msg.role == "user"
        assert msg.content == "hi"

    def test_get_history_dicts(self):
        session = Session()
        session.add_message("user", "Hello")
        session.add_message("assistant", "World")
        dicts = session.get_history_dicts()
        assert dicts == [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "World"},
        ]

    def test_clear(self):
        session = Session()
        session.add_message("user", "test")
        session.clear()
        assert len(session) == 0

    def test_metadata(self):
        session = Session()
        session.metadata["user_name"] = "Alice"
        assert session.metadata["user_name"] == "Alice"

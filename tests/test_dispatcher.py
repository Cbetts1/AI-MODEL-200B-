"""tests/test_dispatcher.py — Unit tests for aura.core.dispatcher."""

import pytest
from aura.tools.registry import ToolRegistry
from aura.core.dispatcher import Dispatcher, DispatchResult


@pytest.fixture
def dispatcher():
    return Dispatcher(tool_registry=ToolRegistry())


class TestDispatcher:
    def test_chat_dispatch(self, dispatcher):
        result = dispatcher.dispatch("Hello, how are you?")
        assert result.kind == "chat"
        assert result.name is None

    def test_tool_dispatch(self, dispatcher):
        result = dispatcher.dispatch("/tool shell ls -la")
        assert result.kind == "tool"
        assert result.name == "shell"
        assert result.args.strip() == "ls -la"

    def test_workflow_dispatch(self, dispatcher):
        result = dispatcher.dispatch("/workflow app_scaffold MyApp com.example /tmp/out")
        assert result.kind == "workflow"
        assert result.name == "app_scaffold"
        assert "MyApp" in result.args

    def test_tool_no_args(self, dispatcher):
        result = dispatcher.dispatch("/tool shell")
        assert result.kind == "tool"
        assert result.name == "shell"
        assert result.args.strip() == ""

    def test_plain_message_is_chat(self, dispatcher):
        for msg in ["what is 2+2", "write me a poem", "/help", "exit"]:
            result = dispatcher.dispatch(msg)
            assert result.kind == "chat", f"Expected chat for: {msg!r}"

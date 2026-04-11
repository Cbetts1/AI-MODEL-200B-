"""tests/test_agent_loop.py — Tests for the AURA AgentLoop (v0.4.0)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aura.core.agent_loop import AgentLoop, _inject_agent_instructions
from aura.tools.registry import ToolRegistry, Tool


# ── Helpers ────────────────────────────────────────────────────────────────────

class _EchoTool(Tool):
    name = "echo"
    description = "Echo the args back"

    def run(self, args: str) -> str:
        return f"ECHO: {args}"


class _FailTool(Tool):
    name = "fail_tool"
    description = "Always fails"

    def run(self, args: str) -> str:
        raise RuntimeError("tool broke")


def _make_model(replies: list) -> MagicMock:
    model = MagicMock()
    model.complete.side_effect = replies
    return model


def _make_registry(*tools) -> ToolRegistry:
    reg = ToolRegistry()
    for t in tools:
        reg.register(t)
    return reg


BASE_HISTORY = [
    {"role": "system", "content": "You are AURA."},
    {"role": "user", "content": "Previous turn."},
    {"role": "assistant", "content": "Ack."},
]


# ── AgentLoop tests ────────────────────────────────────────────────────────────

class TestAgentLoop:

    def test_plain_reply_no_action(self):
        model = _make_model(["Hello, I can help!"])
        reg = _make_registry(_EchoTool())
        loop = AgentLoop(model, reg)
        result = loop.run(BASE_HISTORY, "Hi there")
        assert result == "Hello, I can help!"

    def test_answer_extracted_correctly(self):
        model = _make_model([
            "Thought: I know the answer.\nAnswer: 42 is the answer."
        ])
        reg = _make_registry()
        loop = AgentLoop(model, reg)
        result = loop.run([], "What is the answer?")
        assert result == "42 is the answer."

    def test_tool_call_then_answer(self):
        model = _make_model([
            "Thought: I need to echo.\nAction: echo hello world",
            "Thought: Done.\nAnswer: The echo was ECHO: hello world",
        ])
        reg = _make_registry(_EchoTool())
        loop = AgentLoop(model, reg)
        result = loop.run([], "Echo something")
        assert "ECHO: hello world" in result

    def test_tool_call_appends_observation(self):
        calls = []

        class _TrackingModel:
            def complete(self, messages):
                calls.append(messages)
                if len(calls) == 1:
                    return "Thought: Need echo.\nAction: echo test"
                return "Thought: Got it.\nAnswer: Done."

            def is_available(self):
                return True

        reg = _make_registry(_EchoTool())
        loop = AgentLoop(_TrackingModel(), reg)
        loop.run([], "Do the echo")
        # Second call should include Observation
        assert len(calls) >= 2
        last_messages = calls[-1]
        observations = [m["content"] for m in last_messages if "Observation:" in m.get("content", "")]
        assert len(observations) >= 1

    def test_unknown_tool_returns_error_observation(self):
        model = _make_model([
            "Action: nonexistent_tool arg",
            "Thought: Error.\nAnswer: Could not use tool.",
        ])
        reg = _make_registry(_EchoTool())
        loop = AgentLoop(model, reg)
        result = loop.run([], "Use a missing tool")
        # Should not raise; should return some answer
        assert isinstance(result, str)

    def test_failing_tool_handled_gracefully(self):
        model = _make_model([
            "Action: fail_tool args",
            "Thought: Tool failed.\nAnswer: I got an error.",
        ])
        reg = _make_registry(_FailTool())
        loop = AgentLoop(model, reg)
        result = loop.run([], "Try to fail")
        assert isinstance(result, str)

    def test_max_iterations_reached(self):
        # Model always returns an Action, forcing max iterations
        model = _make_model(["Action: echo loop\n"] * 20)
        reg = _make_registry(_EchoTool())
        loop = AgentLoop(model, reg, max_iterations=3)
        # Should not raise; returns last model output
        result = loop.run([], "Infinite action")
        assert isinstance(result, str)

    def test_empty_history(self):
        model = _make_model(["Answer: This is fine."])
        reg = _make_registry()
        loop = AgentLoop(model, reg)
        result = loop.run([], "Hello")
        assert result == "This is fine."

    def test_tool_summary_included_in_system(self):
        captured = []

        class _CapturingModel:
            def complete(self, messages):
                captured.extend(messages)
                return "Answer: done"

            def is_available(self):
                return True

        reg = _make_registry(_EchoTool())
        loop = AgentLoop(_CapturingModel(), reg)
        loop.run([{"role": "system", "content": "base"}], "test")
        # The system message should contain the tool description
        system_msgs = [m for m in captured if m["role"] == "system"]
        assert len(system_msgs) >= 1
        combined = " ".join(m["content"] for m in system_msgs)
        assert "echo" in combined.lower()


# ── _inject_agent_instructions ─────────────────────────────────────────────────

class TestInjectAgentInstructions:

    def test_appends_to_existing_system_message(self):
        history = [
            {"role": "system", "content": "You are AURA."},
            {"role": "user", "content": "Hi"},
        ]
        result = _inject_agent_instructions(history, " Extra instructions.")
        assert result[0]["role"] == "system"
        assert "You are AURA." in result[0]["content"]
        assert "Extra instructions." in result[0]["content"]

    def test_prepends_system_if_none_exists(self):
        history = [{"role": "user", "content": "Hi"}]
        result = _inject_agent_instructions(history, "Instructions here.")
        assert result[0]["role"] == "system"
        assert "Instructions here." in result[0]["content"]

    def test_does_not_modify_original_history(self):
        history = [{"role": "system", "content": "original"}]
        _inject_agent_instructions(history, " added")
        assert history[0]["content"] == "original"  # original unchanged

    def test_only_first_system_message_extended(self):
        history = [
            {"role": "system", "content": "first"},
            {"role": "system", "content": "second"},
        ]
        result = _inject_agent_instructions(history, " extra")
        assert "extra" in result[0]["content"]
        assert "extra" not in result[1]["content"]


# ── Integration with engine config ────────────────────────────────────────────

class TestEngineRouterBackend:
    """Test that the engine correctly loads router and free backends from config."""

    def test_engine_build_router_backend(self):
        from aura.core.engine import _build_model_from_config
        from aura.model.router import ModelRouter

        cfg = {
            "model": {
                "backend": "router",
                "router": [
                    {"name": "echo", "base_url": ""},
                ],
            }
        }
        model = _build_model_from_config(cfg)
        assert isinstance(model, ModelRouter)

    def test_engine_build_free_backend(self):
        from aura.core.engine import _build_model_from_config
        from aura.model.router import ModelRouter

        cfg = {"model": {"backend": "free"}}
        model = _build_model_from_config(cfg)
        assert isinstance(model, ModelRouter)

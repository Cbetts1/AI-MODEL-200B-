"""aura/core/agent_loop.py — Multi-step agentic tool use for AURA v0.4.0.

The AgentLoop allows AURA to autonomously decide when to call tools, chain
multiple tool calls together, and synthesise a final answer from the results.

This is a simple "ReAct-style" loop:
  1. Model produces a Thought + (optional) Action line.
  2. If an Action is present, the tool is called and its output appended.
  3. Loop repeats until the model produces a final Answer (no Action).
  4. Max iterations guard against infinite loops.

The protocol uses a structured format that works with any chat model:

  Thought: I need to check the weather in Tokyo.
  Action: weather Tokyo
  Observation: 🌤 Tokyo: 18°C, Partly Cloudy, Wind: 12 km/h NE
  Thought: I have the weather. I can now answer.
  Answer: The weather in Tokyo right now is 18°C and partly cloudy.

Usage
-----
    from aura.core.agent_loop import AgentLoop
    loop = AgentLoop(model, tool_registry, max_iterations=6)
    reply = loop.run(conversation_history, "What's the weather in Tokyo?")
"""

from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..model.base import ModelBackend
    from ..tools.registry import ToolRegistry

log = logging.getLogger(__name__)

_ACTION_RE = re.compile(r"^Action:\s*(\w+)\s*(.*)", re.MULTILINE | re.DOTALL)
_ANSWER_RE = re.compile(r"^Answer:\s*(.*)", re.MULTILINE | re.DOTALL)

_AGENT_SYSTEM_ADDENDUM = """\

You also have access to tools.  When you need a tool, use this exact format:

  Thought: <why you need the tool>
  Action: <tool_name> <args>

After the tool runs you will see:
  Observation: <tool output>

When you have enough information to answer, write:
  Thought: <final reasoning>
  Answer: <your full reply to the user>

Available tools:
{tool_summary}

Only call one tool per turn.  If no tool is needed, reply directly (no
Thought/Action/Answer wrapper required).
"""


class AgentLoop:
    """Run a multi-step ReAct loop and return a final answer."""

    def __init__(
        self,
        model: "ModelBackend",
        tool_registry: "ToolRegistry",
        max_iterations: int = 6,
    ) -> None:
        self.model = model
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations

    def run(
        self,
        base_history: List[Dict[str, str]],
        user_message: str,
    ) -> str:
        """Execute the agentic loop and return the final response.

        Parameters
        ----------
        base_history:
            The conversation history so far (system + prior turns).
        user_message:
            The latest user message that triggered the agent loop.
        """
        # Build an agent-specific system addendum with tool descriptions
        tool_summary = self.tool_registry.summary()
        agent_sys = _AGENT_SYSTEM_ADDENDUM.format(tool_summary=tool_summary)

        # Clone history and inject the agent instructions into the system prompt
        history = list(base_history)
        # Find and extend the system message, or prepend one
        agent_history = _inject_agent_instructions(history, agent_sys)
        agent_history.append({"role": "user", "content": user_message})

        for iteration in range(self.max_iterations):
            raw = self.model.complete(agent_history)
            log.debug("AgentLoop iter=%d raw=%r", iteration, raw[:120])

            # Check for a final Answer
            answer_match = _ANSWER_RE.search(raw)
            if answer_match:
                return answer_match.group(1).strip()

            # Check for an Action (tool call)
            action_match = _ACTION_RE.search(raw)
            if action_match:
                tool_name = action_match.group(1).strip()
                tool_args = action_match.group(2).strip()
                observation = self._call_tool(tool_name, tool_args)
                # Append the model's reasoning + the observation
                agent_history.append({"role": "assistant", "content": raw})
                agent_history.append({
                    "role": "user",
                    "content": f"Observation: {observation}",
                })
                continue

            # No Action or Answer — treat as a plain chat reply
            return raw

        # Fallback if max iterations reached: return the last model output
        log.warning("AgentLoop: max iterations (%d) reached", self.max_iterations)
        return raw  # type: ignore[return-value]  # defined by last loop iteration

    # ── private ────────────────────────────────────────────────────────────────

    def _call_tool(self, name: str, args: str) -> str:
        tool = self.tool_registry.get(name)
        if tool is None:
            return f"[Error] Unknown tool '{name}'. Available: {', '.join(self.tool_registry.list_tools())}"
        try:
            return tool.run(args)
        except Exception as exc:  # noqa: BLE001
            return f"[Error] Tool '{name}' raised: {exc}"


# ── helpers ────────────────────────────────────────────────────────────────────

def _inject_agent_instructions(
    history: List[Dict[str, str]],
    instructions: str,
) -> List[Dict[str, str]]:
    """Return a copy of history with agent instructions appended to system msg."""
    result = []
    injected = False
    for msg in history:
        if msg["role"] == "system" and not injected:
            result.append({
                "role": "system",
                "content": msg["content"] + instructions,
            })
            injected = True
        else:
            result.append(dict(msg))
    if not injected:
        result.insert(0, {"role": "system", "content": instructions})
    return result

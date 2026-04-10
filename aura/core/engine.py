"""aura/core/engine.py — The central AuraEngine.

AuraEngine ties together:
  - Identity  : who AURA is (persona.py)
  - Session   : the live conversation state
  - Memory    : persistence layer
  - Model     : LLM backend (local or remote)
  - Dispatcher: routes messages to chat / tool / workflow
  - Tools     : callable tools registry
  - Workflows : multi-step orchestration

Usage example
-------------
    from aura.core.engine import AuraEngine
    engine = AuraEngine.from_config("config/aura.yaml")
    reply = engine.chat("Hello, who are you?")
    print(reply)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from .session import Session
from .memory import AuraMemory
from .dispatcher import Dispatcher
from ..model.base import ModelBackend
from ..tools.registry import ToolRegistry
from ..identity.persona import Persona


class AuraEngine:
    """Orchestrates all AURA sub-systems for a single conversation."""

    def __init__(
        self,
        model: ModelBackend,
        persona: Persona,
        tool_registry: Optional[ToolRegistry] = None,
        memory_dir: Optional[str] = None,
        resume_session_id: Optional[str] = None,
    ) -> None:
        self.model = model
        self.persona = persona
        self.tool_registry = tool_registry or ToolRegistry()
        self.memory = AuraMemory(memory_dir)
        self.session = Session()
        self.dispatcher = Dispatcher(tool_registry=self.tool_registry)

        # Seed the session with AURA's system prompt
        self.session.add_message("system", persona.system_prompt())

        # Optionally restore a previous session from disk
        if resume_session_id:
            self.session.conversation_id = resume_session_id
            self.memory.load(self.session)

    # ── factory ────────────────────────────────────────────────────────────────

    @classmethod
    def from_config(cls, config_path: str = "config/aura.yaml") -> "AuraEngine":
        """Build an AuraEngine from a YAML config file."""
        cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        persona = Persona.from_config("config/identity.yaml")
        model = _build_model_from_config(cfg)
        return cls(
            model=model,
            persona=persona,
            memory_dir=cfg.get("memory", {}).get("dir"),
        )

    # ── public API ─────────────────────────────────────────────────────────────

    def chat(self, user_message: str) -> str:
        """Send a message, dispatch it, and return AURA's reply.

        Handles tool calls, workflow triggers, and plain chat turns.
        """
        self.session.add_message("user", user_message)
        result = self.dispatcher.dispatch(user_message)

        if result.kind == "tool":
            reply = self._run_tool(result.name, result.args)
        elif result.kind == "workflow":
            reply = self._run_workflow(result.name, result.args)
        else:
            reply = self.model.complete(self.session.get_history_dicts())

        self.session.add_message("assistant", reply)
        self.memory.save(self.session)
        return reply

    def reset(self) -> None:
        """Clear history and start a fresh conversation."""
        self.session.clear()
        self.session.add_message("system", self.persona.system_prompt())

    # ── private helpers ────────────────────────────────────────────────────────

    def _run_tool(self, name: str, args: str) -> str:
        tool = self.tool_registry.get(name)
        if tool is None:
            return f"[AURA] Unknown tool: '{name}'. Try /tool list."
        try:
            return tool.run(args)
        except Exception as exc:  # noqa: BLE001
            return f"[AURA] Tool '{name}' raised an error: {exc}"

    def _run_workflow(self, name: str, args: str) -> str:
        # Workflow registry is kept simple at v0.1 — import on demand.
        try:
            from ..workflows.app_scaffold import AppScaffoldWorkflow  # noqa: PLC0415
            workflows = {"app_scaffold": AppScaffoldWorkflow}
            WorkflowClass = workflows.get(name)
            if WorkflowClass is None:
                return f"[AURA] Unknown workflow: '{name}'."
            wf = WorkflowClass()
            return wf.run(args)
        except Exception as exc:  # noqa: BLE001
            return f"[AURA] Workflow '{name}' raised an error: {exc}"


# ── private factory helper ─────────────────────────────────────────────────────

def _build_model_from_config(cfg: dict) -> ModelBackend:
    """Instantiate the correct backend based on config."""
    backend_name = cfg.get("model", {}).get("backend", "remote")

    if backend_name == "local":
        from ..model.local import LocalModelBackend  # noqa: PLC0415
        local_cfg = cfg["model"]["local"]
        return LocalModelBackend(
            engine=local_cfg.get("engine", "llamacpp"),
            model_path=local_cfg.get("model_path", ""),
        )

    # Default: remote / OpenAI-compatible
    from ..model.remote import RemoteModelBackend  # noqa: PLC0415
    remote_cfg = cfg.get("model", {}).get("remote", {})
    return RemoteModelBackend(
        base_url=remote_cfg.get("base_url", "http://localhost:11434/v1"),
        api_key=remote_cfg.get("api_key", ""),
        model_name=remote_cfg.get("model_name", "llama3"),
    )

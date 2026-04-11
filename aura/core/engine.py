"""aura/core/engine.py — The central AuraEngine.

AuraEngine ties together:
  - Identity  : who AURA is (persona.py)
  - Session   : the live conversation state
  - Memory    : persistence layer
  - Model     : LLM backend (local or remote)
  - Dispatcher: routes messages to chat / tool / workflow
  - Tools     : callable tools registry
  - Workflows : multi-step orchestration
  - Templates : pre-fab persona overlays

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
from ..templates.registry import TemplateRegistry, build_default_template_registry


class AuraEngine:
    """Orchestrates all AURA sub-systems for a single conversation."""

    def __init__(
        self,
        model: ModelBackend,
        persona: Persona,
        tool_registry: Optional[ToolRegistry] = None,
        template_registry: Optional[TemplateRegistry] = None,
        memory_dir: Optional[str] = None,
        resume_session_id: Optional[str] = None,
    ) -> None:
        self.model = model
        self.persona = persona
        self.tool_registry = tool_registry or ToolRegistry()
        self.template_registry = template_registry or build_default_template_registry()
        self.memory = AuraMemory(memory_dir)
        self.session = Session()
        self.dispatcher = Dispatcher(tool_registry=self.tool_registry)
        self.active_template: Optional[str] = None

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
        from ..tools.registry import build_default_registry  # noqa: PLC0415
        cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        persona = Persona.from_config("config/identity.yaml")
        model = _build_model_from_config(cfg)
        return cls(
            model=model,
            persona=persona,
            tool_registry=build_default_registry(),
            template_registry=build_default_template_registry(),
            memory_dir=cfg.get("memory", {}).get("dir"),
        )

    # ── public API ─────────────────────────────────────────────────────────────

    def chat(self, user_message: str) -> str:
        """Send a message, dispatch it, and return AURA's reply.

        Handles tool calls, workflow triggers, template commands, and plain chat turns.
        """
        # Handle template commands before dispatch
        template_reply = self._handle_template_command(user_message)
        if template_reply is not None:
            self.session.add_message("user", user_message)
            self.session.add_message("assistant", template_reply)
            self.memory.save(self.session)
            return template_reply

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
        self.active_template = None
        self.session.add_message("system", self.persona.system_prompt())

    def apply_template(self, template_name: str) -> str:
        """Activate a pre-fab template and return its greeting."""
        template = self.template_registry.get(template_name)
        if template is None:
            return f"[AURA] Unknown template: '{template_name}'. Try /template list."
        self.active_template = template_name
        # Add template overlay as a system message
        self.session.add_message("system", template.system_prompt_overlay)
        return template.greeting

    # ── private helpers ────────────────────────────────────────────────────────

    def _handle_template_command(self, message: str) -> Optional[str]:
        """Check if message is a /template command and handle it."""
        stripped = message.strip()
        if not stripped.startswith("/template"):
            return None

        parts = stripped.split(None, 2)
        if len(parts) < 2:
            return self.template_registry.summary()

        subcmd = parts[1].lower()
        if subcmd == "list":
            return self.template_registry.summary()
        if subcmd == "reset":
            self.active_template = None
            return "🔄 Template reset! I'm back to my default AURA persona."
        if subcmd == "use" and len(parts) >= 3:
            return self.apply_template(parts[2].strip())
        return self.template_registry.summary()

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

    if backend_name == "echo":
        from ..model.dummy import EchoModelBackend  # noqa: PLC0415
        return EchoModelBackend()

    if backend_name == "router":
        from ..model.router import build_router_from_config  # noqa: PLC0415
        router_cfg = cfg.get("model", {}).get("router", [])
        return build_router_from_config(router_cfg)

    if backend_name == "free":
        from ..model.router import build_default_free_router  # noqa: PLC0415
        return build_default_free_router()

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

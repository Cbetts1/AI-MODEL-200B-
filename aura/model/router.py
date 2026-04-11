"""aura/model/router.py — Model Router for AURA v0.4.0.

The ModelRouter tries a prioritised list of model backends in order and
returns the result from the first one that succeeds.  This allows AURA to
automatically fall back to alternative services when the primary backend is
unavailable, unreachable, or returns an error.

Free 200B-class cloud services (all OpenAI-compatible):
  - Groq      : https://console.groq.com       llama-3.3-70b-versatile (free tier)
  - OpenRouter: https://openrouter.ai          many models incl. llama-3.3-70b (free)
  - Together  : https://api.together.xyz       Llama-3.3-70B, Qwen2.5-72B (free credits)
  - HuggingFace: https://huggingface.co/settings/tokens  (Inference API, free tier)
  - Cerebras  : https://inference.cerebras.ai  llama-3.3-70b (free, very fast)

All of these are wired as RemoteModelBackend instances with different base_url
and model_name settings.  No local weights are needed — the model runs on the
provider's cloud infrastructure; your device stays lightweight.

Configuration example (config/aura.yaml):

    model:
      backend: router
      router:
        - name: groq
          base_url: https://api.groq.com/openai/v1
          api_key_env: GROQ_API_KEY
          model_name: llama-3.3-70b-versatile
          max_tokens: 4096
          temperature: 0.7
        - name: openrouter
          base_url: https://openrouter.ai/api/v1
          api_key_env: OPENROUTER_API_KEY
          model_name: meta-llama/llama-3.3-70b-instruct:free
          max_tokens: 4096
        - name: cerebras
          base_url: https://api.cerebras.ai/v1
          api_key_env: CEREBRAS_API_KEY
          model_name: llama-3.3-70b
          max_tokens: 4096
        - name: together
          base_url: https://api.together.xyz/v1
          api_key_env: TOGETHER_API_KEY
          model_name: meta-llama/Llama-3.3-70B-Instruct-Turbo
          max_tokens: 4096
        - name: echo
          base_url: ""   # built-in echo fallback — no API key needed
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

from .base import ModelBackend

log = logging.getLogger(__name__)


class ModelRouter(ModelBackend):
    """Tries a prioritised list of backends and returns the first success.

    Each backend is tried in order.  If it raises an exception the error is
    logged and the next backend is tried.  If all backends fail a
    ``RuntimeError`` is raised describing every failure.

    Parameters
    ----------
    backends:
        Ordered list of (label, ModelBackend) tuples.  The label is used only
        for logging / status reporting.
    """

    def __init__(self, backends: List[tuple]) -> None:
        # backends: list of (name: str, backend: ModelBackend)
        self._backends: List[tuple] = backends  # (name, ModelBackend)

    # ── ModelBackend interface ─────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Return True if at least one backend reports availability."""
        return any(b.is_available() for _, b in self._backends)

    def complete(self, messages: List[Dict[str, str]]) -> str:
        """Try each backend in priority order and return the first reply."""
        errors: List[str] = []
        for name, backend in self._backends:
            try:
                result = backend.complete(messages)
                log.debug("ModelRouter: success via backend %r", name)
                return result
            except Exception as exc:  # noqa: BLE001
                log.warning("ModelRouter: backend %r failed: %s", name, exc)
                errors.append(f"{name}: {exc}")

        raise RuntimeError(
            "All model backends failed.\n" + "\n".join(errors)
        )

    # ── status / introspection ─────────────────────────────────────────────────

    def backend_status(self) -> List[Dict[str, object]]:
        """Return a status report for every configured backend.

        Returns a list of dicts:
          {"name": str, "available": bool, "type": str}
        """
        result = []
        for name, backend in self._backends:
            try:
                avail = backend.is_available()
            except Exception:  # noqa: BLE001
                avail = False
            result.append({
                "name": name,
                "available": avail,
                "type": type(backend).__name__,
            })
        return result

    def list_backends(self) -> List[str]:
        """Return just the list of backend names."""
        return [name for name, _ in self._backends]

    def __repr__(self) -> str:
        names = ", ".join(self.list_backends())
        return f"<ModelRouter backends=[{names}]>"


# ── factory helpers ────────────────────────────────────────────────────────────

def build_router_from_config(router_cfg: List[dict]) -> "ModelRouter":
    """Build a ModelRouter from a list of backend config dicts.

    Each entry in ``router_cfg`` is a dict with at minimum:
      - name       : human-readable label
      - base_url   : OpenAI-compatible endpoint (empty → EchoModelBackend)
      - model_name : model identifier on that endpoint

    Optional fields:
      - api_key        : literal API key (prefer api_key_env for security)
      - api_key_env    : name of environment variable holding the API key
      - temperature    : float, default 0.7
      - max_tokens     : int, default 4096
    """
    from .remote import RemoteModelBackend  # noqa: PLC0415
    from .dummy import EchoModelBackend     # noqa: PLC0415

    backends: List[tuple] = []
    for entry in router_cfg:
        name = entry.get("name", "unnamed")
        base_url = entry.get("base_url", "")

        # Built-in echo fallback needs no URL or key
        if not base_url or name == "echo":
            backends.append((name, EchoModelBackend()))
            continue

        # Resolve API key: explicit value wins over env var
        api_key = entry.get("api_key", "")
        if not api_key:
            env_var = entry.get("api_key_env", "")
            if env_var:
                api_key = os.environ.get(env_var, "")

        backend = RemoteModelBackend(
            base_url=base_url,
            api_key=api_key,
            model_name=entry.get("model_name", "llama3"),
            temperature=float(entry.get("temperature", 0.7)),
            max_tokens=int(entry.get("max_tokens", 4096)),
        )
        backends.append((name, backend))

    if not backends:
        # Always have a fallback so the router never crashes
        backends.append(("echo", EchoModelBackend()))

    return ModelRouter(backends)


def build_default_free_router() -> "ModelRouter":
    """Return a ModelRouter pre-configured for free 200B-class cloud services.

    Each service is wired from its standard environment variable.  Set any
    (or all) of the following to unlock that backend:

      GROQ_API_KEY        → Groq  (llama-3.3-70b-versatile, free tier)
      OPENROUTER_API_KEY  → OpenRouter (meta-llama/llama-3.3-70b:free)
      CEREBRAS_API_KEY    → Cerebras  (llama-3.3-70b, ultra-fast)
      TOGETHER_API_KEY    → Together AI (Llama-3.3-70B-Instruct-Turbo)
      HUGGINGFACE_API_KEY → HuggingFace Inference (microsoft/Phi-4, free)

    If no environment variables are set, the router falls back to the built-in
    echo backend so AURA still starts up successfully.
    """
    cfg = [
        {
            "name": "groq",
            "base_url": "https://api.groq.com/openai/v1",
            "api_key_env": "GROQ_API_KEY",
            "model_name": "llama-3.3-70b-versatile",
            "temperature": 0.7,
            "max_tokens": 4096,
        },
        {
            "name": "cerebras",
            "base_url": "https://api.cerebras.ai/v1",
            "api_key_env": "CEREBRAS_API_KEY",
            "model_name": "llama-3.3-70b",
            "temperature": 0.7,
            "max_tokens": 4096,
        },
        {
            "name": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key_env": "OPENROUTER_API_KEY",
            "model_name": "meta-llama/llama-3.3-70b-instruct:free",
            "temperature": 0.7,
            "max_tokens": 4096,
        },
        {
            "name": "together",
            "base_url": "https://api.together.xyz/v1",
            "api_key_env": "TOGETHER_API_KEY",
            "model_name": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "temperature": 0.7,
            "max_tokens": 4096,
        },
        {
            "name": "huggingface",
            "base_url": "https://api-inference.huggingface.co/v1",
            "api_key_env": "HUGGINGFACE_API_KEY",
            "model_name": "microsoft/Phi-4",
            "temperature": 0.7,
            "max_tokens": 2048,
        },
        {
            "name": "echo",
            "base_url": "",
        },
    ]
    return build_router_from_config(cfg)

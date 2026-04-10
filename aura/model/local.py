"""aura/model/local.py — Local inference backend.

Supports two local engines:
  - llamacpp : uses the `llama-cpp-python` package for direct .gguf inference.
  - ollama   : uses the `ollama` Python client which talks to a local Ollama server.

Both engines are **optional dependencies** — if the relevant package is not
installed, `is_available()` returns False and a helpful error is raised.

Configuration example (config/aura.yaml):

    model:
      backend: local
      local:
        engine: llamacpp        # or "ollama"
        model_path: models/weights/model.gguf
        context_length: 4096
        n_threads: 4
"""

from __future__ import annotations

from typing import List, Dict

from .base import ModelBackend


class LocalModelBackend(ModelBackend):
    """Runs inference locally via llama.cpp or Ollama."""

    def __init__(
        self,
        engine: str = "llamacpp",
        model_path: str = "",
        context_length: int = 4096,
        n_threads: int = 4,
        model_name: str = "llama3",   # used only by Ollama engine
    ) -> None:
        self.engine = engine.lower()
        self.model_path = model_path
        self.context_length = context_length
        self.n_threads = n_threads
        self.model_name = model_name
        self._llm = None  # lazy-loaded on first call

    # ── ModelBackend interface ─────────────────────────────────────────────────

    def is_available(self) -> bool:
        if self.engine == "llamacpp":
            import importlib.util
            return (
                importlib.util.find_spec("llama_cpp") is not None
                and bool(self.model_path)
            )
        if self.engine == "ollama":
            import importlib.util
            return importlib.util.find_spec("ollama") is not None
        return False

    def complete(self, messages: List[Dict[str, str]]) -> str:
        """Run local inference and return the assistant reply."""
        if self.engine == "llamacpp":
            return self._complete_llamacpp(messages)
        if self.engine == "ollama":
            return self._complete_ollama(messages)
        raise ValueError(f"Unknown local engine: {self.engine!r}")

    # ── private helpers ────────────────────────────────────────────────────────

    def _complete_llamacpp(self, messages: List[Dict[str, str]]) -> str:
        try:
            from llama_cpp import Llama  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "llama-cpp-python is not installed. "
                "Run: pip install llama-cpp-python"
            ) from exc

        if self._llm is None:
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=self.context_length,
                n_threads=self.n_threads,
                verbose=False,
            )

        response = self._llm.create_chat_completion(messages=messages)
        return response["choices"][0]["message"]["content"]

    def _complete_ollama(self, messages: List[Dict[str, str]]) -> str:
        try:
            import ollama  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "ollama Python client is not installed. Run: pip install ollama"
            ) from exc

        response = ollama.chat(model=self.model_name, messages=messages)
        return response["message"]["content"]

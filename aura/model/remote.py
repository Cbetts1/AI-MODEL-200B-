"""aura/model/remote.py — Remote OpenAI-compatible backend.

Connects to any server that implements the OpenAI Chat Completions API:
  - OpenAI itself
  - Ollama (served at localhost:11434/v1)
  - LM Studio
  - vLLM
  - LocalAI
  - Any other compatible endpoint

Configuration example (config/aura.yaml):

    model:
      backend: remote
      remote:
        base_url: http://localhost:11434/v1
        api_key: ""               # leave blank for local servers
        model_name: llama3
        temperature: 0.7
        max_tokens: 2048
"""

from __future__ import annotations

from typing import List, Dict

from .base import ModelBackend


class RemoteModelBackend(ModelBackend):
    """Calls a remote OpenAI-compatible Chat Completions endpoint."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        api_key: str = "",
        model_name: str = "llama3",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None  # lazy-loaded

    # ── ModelBackend interface ─────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Ping the /models endpoint to check if the server is reachable."""
        try:
            import requests  # noqa: PLC0415
            url = self.base_url.rstrip("/") + "/models"
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = requests.get(url, headers=headers, timeout=3)
            return resp.status_code == 200
        except Exception:  # noqa: BLE001
            return False

    def complete(self, messages: List[Dict[str, str]]) -> str:
        """Send messages to the remote endpoint and return the reply."""
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""

    # ── private ────────────────────────────────────────────────────────────────

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI  # noqa: PLC0415
            except ImportError as exc:
                raise RuntimeError(
                    "openai package is not installed. Run: pip install openai"
                ) from exc
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key or "no-key",
            )
        return self._client

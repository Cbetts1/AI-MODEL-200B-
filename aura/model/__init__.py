"""aura.model — model backend sub-package.

Modules
-------
base    : Abstract base class every backend must implement.
local   : Local inference backend (llama.cpp / Ollama).
remote  : Remote OpenAI-compatible backend.
router  : ModelRouter — tries multiple backends in priority order.
          Pre-configured for free 200B-class cloud services (Groq,
          Cerebras, OpenRouter, Together AI, HuggingFace).
"""

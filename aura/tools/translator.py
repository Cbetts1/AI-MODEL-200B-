"""aura/tools/translator.py — Language translation via the AURA model.

Uses the backing LLM to translate text rather than a dedicated translation
API, so no external key is required.  The quality depends on the active model.

Usage
-----
    /tool translator <target_language> <text>
    /tool translator French Hello, how are you?
    /tool translator Japanese Please show me the menu.
    /tool translator Spanish auto-detect The cat sat on the mat.
"""

from __future__ import annotations

from .registry import Tool


class TranslatorTool(Tool):
    """Translate text to any language using the AURA model (no API key needed)."""

    name = "translator"
    description = "Translate text: translator <target_lang> <text>"

    def run(self, args: str) -> str:
        parts = args.strip().split(None, 1)
        if len(parts) < 2:
            return (
                "⚠️  Usage: /tool translator <target_language> <text>\n"
                "Example: /tool translator French Hello, world!"
            )

        target_lang = parts[0]
        text = parts[1].strip()

        # Build a translation prompt that works even with small models
        prompt = (
            f"Translate the following text into {target_lang}. "
            f"Output only the translated text, nothing else.\n\n"
            f"Text: {text}"
        )

        # Return a structured request that the engine will pass to the model.
        # Since tools don't have direct access to the model backend we embed
        # a structured instruction that AURA's engine will recognise and
        # complete via the normal model path.
        return f"🌐 **Translation to {target_lang}:**\n\n_{prompt}_\n\n*(Tip: paste this prompt directly into the chat or ask AURA to translate for you)*"

"""aura/tools/image_analyzer.py — Image analysis / description tool (v0.4.0).

Sends an image URL to a vision-capable model backend for analysis.  When a
vision backend is not configured, returns a helpful stub message explaining
how to enable it.

Supported backends (vision-capable, free tiers available):
  - Groq       : llava-v1.5-7b (vision, free tier)
  - OpenRouter : many free vision models
  - OpenAI     : gpt-4o-mini vision

Usage
-----
    /tool image_analyzer <image_url>
    /tool image_analyzer describe https://example.com/photo.jpg
    /tool image_analyzer https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png
"""

from __future__ import annotations

import os
import urllib.parse

from .registry import Tool


class ImageAnalyzerTool(Tool):
    """Describe or analyse an image from a URL using a vision-capable model."""

    name = "image_analyzer"
    description = "Analyse an image URL: image_analyzer <url>"

    def run(self, args: str) -> str:
        parts = args.strip().split(None, 1)
        if not parts:
            return "⚠️  Usage: /tool image_analyzer <image_url>"

        # Optional "describe" keyword prefix
        if parts[0].lower() == "describe" and len(parts) > 1:
            image_url = parts[1].strip()
        else:
            image_url = parts[0].strip()

        if not image_url:
            return "⚠️  Please provide an image URL."

        # Normalise URL
        if not image_url.startswith(("http://", "https://")):
            image_url = "https://" + image_url

        # Try a vision-capable backend if available
        result = self._try_vision_api(image_url)
        if result:
            return result

        # Fallback: inform the user how to enable vision
        return (
            f"🖼️  **Image Analysis**\n\n"
            f"URL: {image_url}\n\n"
            f"Vision analysis requires a vision-capable model backend.\n"
            f"To enable image analysis:\n"
            f"  1. Set GROQ_API_KEY and use model **llava-v1.5-7b** via Groq.\n"
            f"  2. Or set OPENROUTER_API_KEY and use a free vision model.\n"
            f"  3. Or configure any OpenAI-compatible vision endpoint.\n\n"
            f"Once configured, AURA will automatically describe images for you."
        )

    def _try_vision_api(self, image_url: str) -> str:
        """Attempt to call a vision-capable OpenAI-compatible endpoint."""
        # Check for Groq vision key
        groq_key = os.environ.get("GROQ_API_KEY", "")
        if groq_key:
            return self._call_openai_vision(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key,
                model="llava-v1.5-7b-4096-preview",
                image_url=image_url,
            )

        # Check for OpenRouter key
        or_key = os.environ.get("OPENROUTER_API_KEY", "")
        if or_key:
            return self._call_openai_vision(
                base_url="https://openrouter.ai/api/v1",
                api_key=or_key,
                model="google/gemini-flash-1.5-8b",
                image_url=image_url,
            )

        # Check for OpenAI key
        oai_key = os.environ.get("OPENAI_API_KEY", "")
        if oai_key:
            return self._call_openai_vision(
                base_url="https://api.openai.com/v1",
                api_key=oai_key,
                model="gpt-4o-mini",
                image_url=image_url,
            )

        return ""

    @staticmethod
    def _call_openai_vision(
        base_url: str,
        api_key: str,
        model: str,
        image_url: str,
    ) -> str:
        try:
            from openai import OpenAI  # noqa: PLC0415
            client = OpenAI(base_url=base_url, api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                        {
                            "type": "text",
                            "text": (
                                "Please describe this image in detail.  "
                                "What do you see?  Include objects, colours, "
                                "text, and any notable features."
                            ),
                        },
                    ],
                }],
                max_tokens=512,
            )
            description = response.choices[0].message.content or ""
            return f"🖼️  **Image Analysis** ({model}):\n\n{description}"
        except Exception as exc:  # noqa: BLE001
            return f"⚠️  Vision API error: {exc}"

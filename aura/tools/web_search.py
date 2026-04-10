"""aura/tools/web_search.py — Web search tool.

Performs a simple web search using the DuckDuckGo Instant Answer API
(no API key required, JSON endpoint, free for non-commercial use).

Usage (in chat)
---------------
    /tool web_search python asyncio tutorial
    /tool web_search latest llama model release

The tool returns a summary from DuckDuckGo's Instant Answer (Abstract)
plus up to 3 related topics.

Note: For a richer search experience, replace the backend here with a
      SerpAPI, Brave Search, or Bing Search integration.
"""

from __future__ import annotations

from .registry import Tool

_DDG_URL = "https://api.duckduckgo.com/"


class WebSearchTool(Tool):
    """Search the web using DuckDuckGo Instant Answers."""

    name = "web_search"
    description = "Search the web. Usage: /tool web_search <query>"

    def run(self, args: str) -> str:
        query = args.strip()
        if not query:
            return "[web_search] Please provide a search query."

        try:
            import requests  # noqa: PLC0415
        except ImportError:
            return "[web_search] 'requests' package not installed. Run: pip install requests"

        try:
            resp = requests.get(
                _DDG_URL,
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
                timeout=10,
                headers={"User-Agent": "AURA/0.1 (+https://github.com/Cbetts1/AI-MODEL-200B-)"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            return f"[web_search] Request failed: {exc}"

        lines: list[str] = []

        abstract = data.get("AbstractText", "").strip()
        abstract_source = data.get("AbstractSource", "")
        if abstract:
            lines.append(f"**{abstract_source}**: {abstract}")

        answer = data.get("Answer", "").strip()
        if answer:
            lines.append(f"**Direct answer**: {answer}")

        related = data.get("RelatedTopics", [])[:3]
        if related:
            lines.append("\nRelated topics:")
            for topic in related:
                if isinstance(topic, dict) and "Text" in topic:
                    lines.append(f"  • {topic['Text']}")

        if not lines:
            lines.append(
                f"No instant answer found for '{query}'. "
                "Try a more specific query or check a search engine directly."
            )

        return "\n".join(lines)

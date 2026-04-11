"""aura/tools/url_reader.py — Fetch and extract the text content of a URL.

Fetches a web page over HTTP and strips the HTML to return readable plain
text.  Useful for letting AURA reference live web content without a
dedicated search API.

Usage
-----
    /tool url_reader https://example.com
    /tool url_reader https://en.wikipedia.org/wiki/Python_(programming_language)
"""

from __future__ import annotations

import re
import urllib.request
from html.parser import HTMLParser

from .registry import Tool

# Tags whose contents we completely skip (scripts, styles, etc.)
_SKIP_TAGS = frozenset({
    "script", "style", "noscript", "head", "meta", "link",
    "nav", "footer", "aside", "header",
})

# Inline tags (don't add newlines around them)
_INLINE_TAGS = frozenset({
    "a", "span", "em", "strong", "b", "i", "code", "small",
    "sub", "sup", "label", "abbr",
})

_MAX_CHARS = 4000  # truncate output to keep context manageable


class _TextExtractor(HTMLParser):
    """Minimal HTML → plain-text converter."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list = []
        self._skip_depth: int = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in ("p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"):
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._parts)
        # Collapse whitespace runs while preserving single newlines
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


class URLReaderTool(Tool):
    """Fetch a URL and return its readable text content."""

    name = "url_reader"
    description = "Fetch and read the text content of a URL"

    def run(self, args: str) -> str:
        url = args.strip()
        if not url:
            return "⚠️  Usage: /tool url_reader <url>"

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; AURA-url-reader/0.4.0)"
                    )
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                content_type = resp.headers.get("Content-Type", "")
                raw_bytes = resp.read(65536)  # limit to 64 KB

            if "html" not in content_type.lower():
                # Return raw text for non-HTML (JSON, plain text, etc.)
                text = raw_bytes.decode("utf-8", errors="replace")
                text = text[:_MAX_CHARS]
                return f"📄 Content from {url}:\n\n{text}"

            html = raw_bytes.decode("utf-8", errors="replace")
            parser = _TextExtractor()
            parser.feed(html)
            text = parser.get_text()

            if len(text) > _MAX_CHARS:
                text = text[:_MAX_CHARS] + "\n\n…[truncated]"

            return f"🌐 Content from {url}:\n\n{text}"

        except Exception as exc:  # noqa: BLE001
            return f"⚠️  Failed to fetch '{url}': {exc}"

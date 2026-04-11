"""aura/tools/summarizer.py — Text summarization and note-taking tool.

Provides quick summarization of text using extractive techniques (no external
model required).  Picks the most informative sentences based on word frequency.

Usage (in chat)
---------------
    /tool summarizer <long text to summarize>
    /tool summarizer --sentences 3 <text>
"""

from __future__ import annotations

import re
from collections import Counter

from .registry import Tool

DEFAULT_SENTENCES = 3


def _extractive_summary(text: str, num_sentences: int = DEFAULT_SENTENCES) -> str:
    """Return the top *num_sentences* most informative sentences from *text*.

    Uses a simple word-frequency scoring heuristic:
      1. Tokenise text into sentences.
      2. Count word frequencies across the entire text (stopwords excluded).
      3. Score each sentence by summing frequencies of its words.
      4. Return the highest-scoring sentences in their original order.
    """
    # Simple sentence splitting
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) <= num_sentences:
        return text.strip()

    # Stopwords (small set, no external dependency)
    stopwords = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "shall",
        "should", "may", "might", "can", "could", "must", "to", "of", "in",
        "for", "on", "with", "at", "by", "from", "as", "into", "through",
        "during", "before", "after", "above", "below", "and", "but", "or",
        "nor", "not", "so", "yet", "both", "either", "neither", "this",
        "that", "these", "those", "it", "its", "i", "me", "my", "we", "our",
        "you", "your", "he", "she", "they", "them", "their", "which", "what",
    }

    def tokenize(s: str) -> list[str]:
        return [w.lower() for w in re.findall(r'\b[a-z]+\b', s.lower()) if w not in stopwords]

    # Word frequencies
    all_words = tokenize(text)
    freq = Counter(all_words)

    # Score sentences
    scored = []
    for idx, sent in enumerate(sentences):
        words = tokenize(sent)
        score = sum(freq.get(w, 0) for w in words)
        scored.append((score, idx, sent))

    # Pick top sentences, preserve original order
    scored.sort(key=lambda x: x[0], reverse=True)
    top = sorted(scored[:num_sentences], key=lambda x: x[1])
    return " ".join(s[2] for s in top)


class SummarizerTool(Tool):
    """Summarize a block of text into key sentences."""

    name = "summarizer"
    description = "Summarize text. Usage: /tool summarizer <text>"

    def run(self, args: str) -> str:
        text = args.strip()
        if not text:
            return "[summarizer] Please provide text to summarize."

        # Optional --sentences N flag
        num = DEFAULT_SENTENCES
        match = re.match(r'--sentences\s+(\d+)\s+', text)
        if match:
            num = int(match.group(1))
            text = text[match.end():]

        if len(text) < 100:
            return f"📝 Text is already short:\n{text}"

        summary = _extractive_summary(text, num_sentences=num)
        return f"📝 **Summary** ({num} key sentences):\n\n{summary}"

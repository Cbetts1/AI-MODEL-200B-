"""aura/tools/notes.py — Persistent named-note tool.

Lets AURA (or the user) save short notes by name and recall them later.
Notes are stored as JSON in the AURA memory directory so they persist across
sessions.

Usage
-----
    /tool notes save  <name>  <content>
    /tool notes get   <name>
    /tool notes list
    /tool notes delete <name>
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .registry import Tool

_NOTES_FILE = Path.home() / ".aura" / "notes.json"


def _load() -> dict:
    if _NOTES_FILE.exists():
        try:
            return json.loads(_NOTES_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _save(notes: dict) -> None:
    _NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    _NOTES_FILE.write_text(json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8")


class NotesTool(Tool):
    """Save and recall named notes that persist across sessions."""

    name = "notes"
    description = "Save/recall named notes: notes save <name> <text> | notes get <name> | notes list"

    def run(self, args: str) -> str:
        parts = args.strip().split(None, 2)
        if not parts:
            return self._help()

        subcmd = parts[0].lower()

        if subcmd == "save":
            if len(parts) < 3:
                return "⚠️  Usage: /tool notes save <name> <content>"
            name, content = parts[1], parts[2]
            notes = _load()
            notes[name] = content
            _save(notes)
            return f"📝 Note '{name}' saved."

        if subcmd == "get":
            if len(parts) < 2:
                return "⚠️  Usage: /tool notes get <name>"
            name = parts[1]
            notes = _load()
            if name not in notes:
                return f"⚠️  No note named '{name}'. Use 'notes list' to see all notes."
            return f"📝 **{name}**:\n{notes[name]}"

        if subcmd == "list":
            notes = _load()
            if not notes:
                return "📓 No notes saved yet. Use 'notes save <name> <text>' to create one."
            lines = ["📓 Saved notes:"]
            for k in sorted(notes):
                preview = notes[k][:60].replace("\n", " ")
                lines.append(f"  • {k}: {preview}…" if len(notes[k]) > 60 else f"  • {k}: {notes[k]}")
            return "\n".join(lines)

        if subcmd == "delete":
            if len(parts) < 2:
                return "⚠️  Usage: /tool notes delete <name>"
            name = parts[1]
            notes = _load()
            if name not in notes:
                return f"⚠️  No note named '{name}'."
            del notes[name]
            _save(notes)
            return f"🗑️  Note '{name}' deleted."

        return self._help()

    @staticmethod
    def _help() -> str:
        return (
            "📝 **Notes tool** — save and recall named notes.\n\n"
            "  notes save <name> <content>   — save a note\n"
            "  notes get <name>              — recall a note\n"
            "  notes list                    — list all notes\n"
            "  notes delete <name>           — delete a note"
        )

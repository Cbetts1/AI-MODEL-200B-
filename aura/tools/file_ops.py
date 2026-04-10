"""aura/tools/file_ops.py — File read / write / list tools.

Provides three tools:
  file_read   : Read a text file and return its content.
  file_write  : Write (or overwrite) a text file.
  file_list   : List files in a directory.

Usage (in chat)
---------------
    /tool file_read /path/to/file.txt
    /tool file_write /path/to/out.txt <content>
    /tool file_list /path/to/dir
"""

from __future__ import annotations

import os
from pathlib import Path

from .registry import Tool

# Maximum bytes read by file_read to prevent accidental memory exhaustion.
MAX_READ_BYTES = 1_000_000  # 1 MB


class FileReadTool(Tool):
    """Read a text file from disk."""

    name = "file_read"
    description = "Read a text file. Usage: /tool file_read <path>"

    def run(self, args: str) -> str:
        path_str = args.strip()
        if not path_str:
            return "[file_read] Please provide a file path."
        path = Path(path_str).expanduser()
        if not path.exists():
            return f"[file_read] File not found: {path}"
        if not path.is_file():
            return f"[file_read] Not a file: {path}"
        try:
            content = path.read_bytes()[:MAX_READ_BYTES].decode("utf-8", errors="replace")
            return content or "(empty file)"
        except Exception as exc:  # noqa: BLE001
            return f"[file_read] Error reading {path}: {exc}"


class FileWriteTool(Tool):
    """Write text content to a file."""

    name = "file_write"
    description = (
        "Write text to a file (overwrites). "
        "Usage: /tool file_write <path> <content>"
    )

    def run(self, args: str) -> str:
        parts = args.strip().split(None, 1)
        if len(parts) < 2:
            return "[file_write] Usage: /tool file_write <path> <content>"
        path_str, content = parts[0], parts[1]
        path = Path(path_str).expanduser()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return f"[file_write] Written {len(content)} characters to {path}."
        except Exception as exc:  # noqa: BLE001
            return f"[file_write] Error writing {path}: {exc}"


class FileListTool(Tool):
    """List files in a directory."""

    name = "file_list"
    description = "List files in a directory. Usage: /tool file_list [path]"

    def run(self, args: str) -> str:
        path_str = args.strip() or "."
        path = Path(path_str).expanduser()
        if not path.exists():
            return f"[file_list] Path not found: {path}"
        if not path.is_dir():
            return f"[file_list] Not a directory: {path}"
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
            if not entries:
                return f"[file_list] {path} is empty."
            lines = [f"Contents of {path}:", ""]
            for entry in entries:
                prefix = "📁 " if entry.is_dir() else "📄 "
                lines.append(f"  {prefix}{entry.name}")
            return "\n".join(lines)
        except Exception as exc:  # noqa: BLE001
            return f"[file_list] Error listing {path}: {exc}"

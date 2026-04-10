"""aura/tools/shell.py — Shell command execution tool.

Allows AURA to run shell commands on the host system.

Usage (in chat)
---------------
    /tool shell ls -la
    /tool shell echo "Hello from AURA"

Security notes
--------------
- This tool runs with the same privileges as the AURA process.
- In production you should wrap this with a sandbox / allow-list.
- The tool captures both stdout and stderr and returns them as a string.
- A configurable timeout prevents runaway commands.
"""

from __future__ import annotations

import shlex
import subprocess

from .registry import Tool

# Maximum seconds a shell command is allowed to run.
DEFAULT_TIMEOUT = 30


class ShellTool(Tool):
    """Execute a shell command and return its output."""

    name = "shell"
    description = "Run a shell command. Usage: /tool shell <command>"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout

    def run(self, args: str) -> str:
        """Run *args* as a shell command string and return combined output."""
        if not args.strip():
            return "[shell] No command provided."
        try:
            result = subprocess.run(
                args,
                shell=True,          # allow pipes, redirects, etc.
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            output = result.stdout
            if result.stderr:
                output += "\n[stderr]\n" + result.stderr
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"
            return output.strip() or "[shell] (no output)"
        except subprocess.TimeoutExpired:
            return f"[shell] Command timed out after {self.timeout}s."
        except Exception as exc:  # noqa: BLE001
            return f"[shell] Error: {exc}"

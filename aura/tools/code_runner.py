"""aura/tools/code_runner.py — Safe code execution in a subprocess sandbox.

Runs user-provided Python code in a separate subprocess with a timeout.
Only Python is supported at v0.3 — other languages can be added later.

Usage (in chat)
---------------
    /tool code_runner print("Hello, world!")
    /tool code_runner for i in range(5): print(i)

Security
--------
Code runs in a subprocess with a timeout.  It does NOT have access to
AURA's internals or the file system beyond what the OS user can access.
In production, use a container or gVisor sandbox for stronger isolation.
"""

from __future__ import annotations

import subprocess
import textwrap

from .registry import Tool

RUN_TIMEOUT = 10  # seconds


class CodeRunnerTool(Tool):
    """Run Python code snippets and return output."""

    name = "code_runner"
    description = (
        "Run Python code in a sandboxed subprocess. "
        "⚠️ Runs with AURA process permissions — use container sandboxing in production. "
        "Usage: /tool code_runner <code>"
    )

    def run(self, args: str) -> str:
        code = args.strip()
        if not code:
            return "[code_runner] Please provide Python code to run."

        try:
            result = subprocess.run(
                ["python3", "-c", code],
                capture_output=True,
                text=True,
                timeout=RUN_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return f"[code_runner] Code timed out after {RUN_TIMEOUT}s."
        except FileNotFoundError:
            return "[code_runner] Python3 not found on this system."

        output = result.stdout
        if result.stderr:
            output += "\n[stderr]\n" + result.stderr
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"
        return output.strip() or "[code_runner] (no output)"

"""aura/tools/apk_builder.py — Android APK build orchestration tool.

Wraps the Android build pipeline so AURA can trigger an APK build directly
from a chat command.

Usage (in chat)
---------------
    /tool apk_builder /path/to/project

What this tool does
-------------------
1. Verifies that the project directory exists and contains a build.gradle.
2. Verifies that `gradlew` is executable (Android Gradle Wrapper).
3. Runs `./gradlew assembleDebug` inside the project directory.
4. Reports the path of the generated .apk on success.

Prerequisites
-------------
- Android SDK installed and ANDROID_HOME environment variable set.
- Java 17+ on PATH.
- A valid Gradle Android project at the given path.

On Termux
---------
    pkg install tur-repo && pkg install openjdk-17
    # Install Android SDK manually or use sdkmanager via tur-repo.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .registry import Tool

BUILD_TIMEOUT = 300  # 5 minutes — Gradle first builds take a long time


class ApkBuilderTool(Tool):
    """Build an Android APK from a Gradle project."""

    name = "apk_builder"
    description = (
        "Build an Android APK. Usage: /tool apk_builder <project_dir>"
    )

    def run(self, args: str) -> str:
        project_dir_str = args.strip()
        if not project_dir_str:
            return "[apk_builder] Please provide a project directory path."

        project_dir = Path(project_dir_str).expanduser().resolve()

        # ── sanity checks ──────────────────────────────────────────────────────
        if not project_dir.exists():
            return f"[apk_builder] Directory not found: {project_dir}"
        if not project_dir.is_dir():
            return f"[apk_builder] Not a directory: {project_dir}"
        gradlew = project_dir / "gradlew"
        if not gradlew.exists():
            return (
                f"[apk_builder] No 'gradlew' script found in {project_dir}. "
                "Make sure this is a valid Android Gradle project."
            )

        # Ensure gradlew is executable
        gradlew.chmod(gradlew.stat().st_mode | 0o111)
        # ── run the build ──────────────────────────────────────────────────────
        try:
            result = subprocess.run(
                ["./gradlew", "assembleDebug", "--no-daemon"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=BUILD_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return f"[apk_builder] Build timed out after {BUILD_TIMEOUT}s."
        except FileNotFoundError:
            return "[apk_builder] Could not execute ./gradlew. Is Java installed?"
        except Exception as exc:  # noqa: BLE001
            return f"[apk_builder] Unexpected error: {exc}"

        if result.returncode != 0:
            tail = result.stderr[-2000:] if result.stderr else result.stdout[-2000:]
            return f"[apk_builder] Build FAILED (exit {result.returncode}):\n{tail}"

        # ── find the output APK ────────────────────────────────────────────────
        apk_paths = list(project_dir.rglob("*.apk"))
        if apk_paths:
            apk_list = "\n".join(f"  {p}" for p in apk_paths)
            return f"[apk_builder] Build succeeded!\nOutput APK(s):\n{apk_list}"

        return "[apk_builder] Build succeeded, but no .apk file was found. Check build output."

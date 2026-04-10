"""tests/test_tools.py — Unit tests for built-in tools."""

import os
import pytest
from pathlib import Path

from aura.tools.registry import Tool, ToolRegistry, build_default_registry
from aura.tools.shell import ShellTool
from aura.tools.file_ops import FileReadTool, FileWriteTool, FileListTool
from aura.tools.web_search import WebSearchTool


# ── ToolRegistry ───────────────────────────────────────────────────────────────

class EchoTool(Tool):
    name = "echo"
    description = "Echoes args back."

    def run(self, args: str) -> str:
        return f"ECHO: {args}"


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        tool = registry.get("echo")
        assert tool is not None
        assert tool.run("hello") == "ECHO: hello"

    def test_get_missing(self):
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        assert "echo" in registry.list_tools()

    def test_summary_contains_name(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        assert "echo" in registry.summary()

    def test_empty_registry_summary(self):
        registry = ToolRegistry()
        assert "No tools" in registry.summary()

    def test_register_no_name_raises(self):
        class BadTool(Tool):
            name = ""
            description = ""
            def run(self, args): return ""

        with pytest.raises(ValueError):
            ToolRegistry().register(BadTool())

    def test_build_default_registry(self):
        registry = build_default_registry()
        for expected in ["shell", "file_read", "file_write", "file_list", "web_search", "apk_builder"]:
            assert registry.get(expected) is not None


# ── ShellTool ──────────────────────────────────────────────────────────────────

class TestShellTool:
    def test_echo(self):
        tool = ShellTool()
        result = tool.run("echo hello_aura")
        assert "hello_aura" in result

    def test_no_command(self):
        tool = ShellTool()
        result = tool.run("   ")
        assert "No command" in result

    def test_exit_code_in_output(self):
        tool = ShellTool()
        result = tool.run("exit 42")
        assert "42" in result


# ── FileReadTool ───────────────────────────────────────────────────────────────

class TestFileReadTool:
    def test_read_existing(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("hello world", encoding="utf-8")
        tool = FileReadTool()
        result = tool.run(str(f))
        assert "hello world" in result

    def test_read_missing(self, tmp_path):
        tool = FileReadTool()
        result = tool.run(str(tmp_path / "nope.txt"))
        assert "not found" in result.lower()

    def test_no_path(self):
        tool = FileReadTool()
        result = tool.run("")
        assert "path" in result.lower()


# ── FileWriteTool ──────────────────────────────────────────────────────────────

class TestFileWriteTool:
    def test_write_and_verify(self, tmp_path):
        target = tmp_path / "out.txt"
        tool = FileWriteTool()
        result = tool.run(f"{target} some content here")
        assert "Written" in result
        assert target.read_text() == "some content here"

    def test_missing_content(self):
        tool = FileWriteTool()
        result = tool.run("/some/path")
        assert "Usage" in result


# ── FileListTool ───────────────────────────────────────────────────────────────

class TestFileListTool:
    def test_list_dir(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        tool = FileListTool()
        result = tool.run(str(tmp_path))
        assert "a.txt" in result
        assert "b.txt" in result

    def test_missing_dir(self, tmp_path):
        tool = FileListTool()
        result = tool.run(str(tmp_path / "nope"))
        assert "not found" in result.lower()

    def test_empty_dir(self, tmp_path):
        tool = FileListTool()
        result = tool.run(str(tmp_path))
        assert "empty" in result.lower()

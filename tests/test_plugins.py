"""tests/test_plugins.py — Tests for aura.plugins.loader (AURA v0.6.0)."""

import textwrap
from pathlib import Path

import pytest

from aura.tools.registry import ToolRegistry, Tool
from aura.plugins.loader import PluginLoader


# ── helpers ────────────────────────────────────────────────────────────────────

def _write_plugin(directory: Path, filename: str, content: str) -> Path:
    """Write a plugin .py file into *directory* and return the path."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


# ── PluginLoader tests ─────────────────────────────────────────────────────────

class TestPluginLoaderLoadFile:
    def test_loads_valid_tool(self, tmp_path):
        plugin_path = _write_plugin(
            tmp_path,
            "greet.py",
            """\
            from aura.tools.registry import Tool

            class GreetTool(Tool):
                name = "greet"
                description = "Greet someone."

                def run(self, args: str) -> str:
                    return f"Hello, {args or 'friend'}!"
            """,
        )
        registry = ToolRegistry()
        loader = PluginLoader(registry, extra_dirs=[tmp_path])
        names = loader.load_file(plugin_path)
        assert "greet" in names
        assert registry.get("greet") is not None

    def test_loaded_tool_runs(self, tmp_path):
        plugin_path = _write_plugin(
            tmp_path,
            "echo_plugin.py",
            """\
            from aura.tools.registry import Tool

            class EchoTool(Tool):
                name = "plugin_echo"
                description = "Echo args."

                def run(self, args: str) -> str:
                    return args
            """,
        )
        registry = ToolRegistry()
        loader = PluginLoader(registry)
        loader.load_file(plugin_path)
        tool = registry.get("plugin_echo")
        assert tool is not None
        assert tool.run("hello") == "hello"

    def test_skips_tool_with_no_name(self, tmp_path):
        plugin_path = _write_plugin(
            tmp_path,
            "noname.py",
            """\
            from aura.tools.registry import Tool

            class NoNameTool(Tool):
                name = ""
                description = "Has no name."

                def run(self, args: str) -> str:
                    return "nope"
            """,
        )
        registry = ToolRegistry()
        loader = PluginLoader(registry)
        names = loader.load_file(plugin_path)
        assert names == []

    def test_does_not_override_builtin(self, tmp_path):
        """Plugin with same name as existing tool should be skipped."""
        plugin_path = _write_plugin(
            tmp_path,
            "clash.py",
            """\
            from aura.tools.registry import Tool

            class ClashTool(Tool):
                name = "existing_tool"
                description = "I clash."

                def run(self, args: str) -> str:
                    return "clash"
            """,
        )
        # Pre-register an existing tool
        class ExistingTool(Tool):
            name = "existing_tool"
            description = "Original."
            def run(self, args: str) -> str:
                return "original"

        registry = ToolRegistry()
        registry.register(ExistingTool())
        loader = PluginLoader(registry)
        loader.load_file(plugin_path)
        # Original should still be there
        assert registry.get("existing_tool").run("") == "original"

    def test_skips_invalid_python(self, tmp_path):
        bad_path = _write_plugin(
            tmp_path,
            "broken.py",
            "this is not valid python !! @@ ##",
        )
        registry = ToolRegistry()
        loader = PluginLoader(registry)
        names = loader.load_file(bad_path)
        assert names == []

    def test_skips_non_tool_class(self, tmp_path):
        plugin_path = _write_plugin(
            tmp_path,
            "notool.py",
            """\
            class NotATool:
                name = "not_a_tool"
                def run(self, args):
                    return "x"
            """,
        )
        registry = ToolRegistry()
        loader = PluginLoader(registry)
        names = loader.load_file(plugin_path)
        assert names == []


class TestPluginLoaderLoadAll:
    def test_load_all_from_directory(self, tmp_path):
        plugin_dir = tmp_path / "plugins"
        _write_plugin(
            plugin_dir,
            "tool_a.py",
            """\
            from aura.tools.registry import Tool
            class ToolA(Tool):
                name = "plugin_a"
                description = "A"
                def run(self, args): return "a"
            """,
        )
        _write_plugin(
            plugin_dir,
            "tool_b.py",
            """\
            from aura.tools.registry import Tool
            class ToolB(Tool):
                name = "plugin_b"
                description = "B"
                def run(self, args): return "b"
            """,
        )
        registry = ToolRegistry()
        loader = PluginLoader(registry, extra_dirs=[plugin_dir])
        # Override default dirs so only our tmp dir is searched
        loader._dirs = [plugin_dir]
        names = loader.load_all()
        assert "plugin_a" in names
        assert "plugin_b" in names

    def test_load_all_empty_dir(self, tmp_path):
        empty_dir = tmp_path / "empty_plugins"
        empty_dir.mkdir()
        registry = ToolRegistry()
        loader = PluginLoader(registry)
        loader._dirs = [empty_dir]
        names = loader.load_all()
        assert names == []

    def test_load_all_nonexistent_dir(self, tmp_path):
        registry = ToolRegistry()
        loader = PluginLoader(registry)
        loader._dirs = [tmp_path / "does_not_exist"]
        names = loader.load_all()
        assert names == []

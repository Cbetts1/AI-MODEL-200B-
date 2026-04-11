"""aura/plugins/loader.py — Dynamic plugin loader for AURA v0.6.0.

The plugin loader discovers Python files in a ``plugins/`` directory and
registers any ``Tool`` subclass found in them automatically.  This lets AURA
expand her capabilities at runtime without modifying core source files.

Plugin discovery order (highest priority first):
  1. ``<cwd>/plugins/``
  2. ``~/.aura/plugins/``
  3. Any extra directories passed to ``PluginLoader.__init__``

Writing a Plugin
----------------
Create a ``.py`` file in one of the discovery directories.  Define one or
more classes that inherit from ``aura.tools.registry.Tool``::

    # plugins/greeting.py
    from aura.tools.registry import Tool

    class GreetingTool(Tool):
        name = "greet"
        description = "Greet someone by name."

        def run(self, args: str) -> str:
            name = args.strip() or "friend"
            return f"Hello, {name}! 👋"

AURA will automatically discover and register this tool on next start.

Safety
------
* Plugin source is never executed until a human deploys the file.
* Plugins are screened by GovernanceEngine before their ``run`` method is
  invoked for the first time.
* Plugins cannot override built-in tools (names collide → warning, skip).
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import List, Optional

from ..tools.registry import Tool, ToolRegistry

log = logging.getLogger(__name__)

_DEFAULT_DIRS = [
    Path.cwd() / "plugins",
    Path.home() / ".aura" / "plugins",
]


class PluginLoader:
    """Discovers and loads external plugin tools into a ToolRegistry.

    Parameters
    ----------
    registry:
        The ToolRegistry to register discovered tools into.
    extra_dirs:
        Additional directories to search (in addition to the defaults).
    """

    def __init__(
        self,
        registry: ToolRegistry,
        extra_dirs: Optional[List[Path]] = None,
    ) -> None:
        self._registry = registry
        self._dirs: List[Path] = list(_DEFAULT_DIRS)
        if extra_dirs:
            self._dirs.extend(extra_dirs)

    # ── public API ─────────────────────────────────────────────────────────────

    def load_all(self) -> List[str]:
        """Scan all plugin directories and register discovered tools.

        Returns
        -------
        list[str]
            Names of tools that were successfully loaded.
        """
        loaded: List[str] = []
        for directory in self._dirs:
            if not directory.is_dir():
                continue
            for py_file in sorted(directory.glob("*.py")):
                names = self._load_file(py_file)
                loaded.extend(names)
        return loaded

    def load_file(self, path: Path) -> List[str]:
        """Load a single plugin file and register any tools found.

        Parameters
        ----------
        path:
            Absolute or relative path to a ``.py`` plugin file.

        Returns
        -------
        list[str]
            Names of tools that were successfully registered.
        """
        return self._load_file(path)

    # ── private ────────────────────────────────────────────────────────────────

    def _load_file(self, path: Path) -> List[str]:
        """Import a plugin file and register Tool subclasses."""
        path = path.resolve()
        module_name = f"aura_plugin_{path.stem}"
        registered: List[str] = []

        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                log.warning("Plugin: could not create spec for %s — skipping", path)
                return registered
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            log.warning("Plugin: failed to import %s: %s", path, exc)
            return registered

        # Find all Tool subclasses defined in this module
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, Tool)
                and obj is not Tool
                and obj.__module__ == module_name
            ):
                try:
                    instance = obj()
                    if not instance.name:
                        log.warning("Plugin class %s has no name — skipping", obj)
                        continue
                    if self._registry.get(instance.name) is not None:
                        log.warning(
                            "Plugin: tool '%s' from %s conflicts with an existing "
                            "tool — skipping to protect built-ins",
                            instance.name,
                            path.name,
                        )
                        continue
                    self._registry.register(instance)
                    registered.append(instance.name)
                    log.info("Plugin loaded: '%s' from %s", instance.name, path.name)
                except Exception as exc:  # noqa: BLE001
                    log.warning("Plugin: could not register %s: %s", obj, exc)

        return registered

"""aura/ui/cli.py — Click-based CLI entry point.

Commands
--------
  aura chat               Interactive REPL chat with AURA.
  aura chat --once MSG    Send a single message and exit.
  aura tools              List all available tools.
  aura version            Print the AURA version.

The CLI reads config/aura.yaml (or the path set by --config) and builds an
AuraEngine automatically.

Usage
-----
    pip install -e .    # installs the `aura` command
    aura --help
    aura chat
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

console = Console()

_DEFAULT_CONFIG = "config/aura.yaml"
_BANNER = "[bold cyan]AURA[/] — [dim]AI Unified Reasoning Architecture[/]"
_EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit", "q"}


# ── helpers ────────────────────────────────────────────────────────────────────

def _load_engine(config_path: str):
    """Import and build AuraEngine; return it. Exits on config error."""
    try:
        from ..core.engine import AuraEngine  # noqa: PLC0415
        return AuraEngine.from_config(config_path)
    except FileNotFoundError:
        console.print(
            f"[red]Config file not found:[/] {config_path}\n"
            "Copy [bold]config/aura.yaml[/] from the repo and edit it."
        )
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Failed to load engine:[/] {exc}")
        sys.exit(1)


def _print_reply(reply: str, name: str = "AURA") -> None:
    console.print(Panel(reply, title=f"[bold cyan]{name}[/]", border_style="cyan"))


# ── CLI root group ─────────────────────────────────────────────────────────────

@click.group()
@click.option(
    "--config",
    default=_DEFAULT_CONFIG,
    show_default=True,
    help="Path to aura.yaml config file.",
)
@click.pass_context
def main(ctx: click.Context, config: str) -> None:
    """AURA — AI Unified Reasoning Architecture CLI."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config


# ── chat command ───────────────────────────────────────────────────────────────

@main.command()
@click.option("--once", default=None, metavar="MESSAGE", help="Send one message and exit.")
@click.option("--session", default=None, metavar="ID", help="Resume a previous session by ID.")
@click.pass_context
def chat(ctx: click.Context, once: str | None, session: str | None) -> None:
    """Start an interactive chat session with AURA."""
    config_path = ctx.obj["config"]
    engine = _load_engine(config_path)

    if session:
        engine.session.conversation_id = session
        engine.memory.load(engine.session)
        console.print(f"[dim]Resumed session {session}[/]")

    if once:
        reply = engine.chat(once)
        _print_reply(reply, engine.persona.name)
        return

    # ── interactive REPL ───────────────────────────────────────────────────────
    console.print(Panel(_BANNER, border_style="cyan", padding=(0, 2)))
    console.print(
        f"[dim]Session ID: {engine.session.conversation_id}[/]\n"
        "[dim]Type 'exit' or Ctrl-C to quit.  /tool list to see tools.[/]\n"
    )

    while True:
        try:
            user_input = Prompt.ask("[bold green]You[/]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/]")
            break

        if user_input.strip().lower() in _EXIT_COMMANDS:
            console.print("[dim]Goodbye.[/]")
            break

        if user_input.strip() == "/tool list":
            console.print(engine.tool_registry.summary())
            continue

        if user_input.strip() == "/reset":
            engine.reset()
            console.print("[dim]Session reset.[/]")
            continue

        try:
            reply = engine.chat(user_input)
            _print_reply(reply, engine.persona.name)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]Error:[/] {exc}")


# ── tools command ──────────────────────────────────────────────────────────────

@main.command(name="tools")
@click.pass_context
def list_tools(ctx: click.Context) -> None:
    """List all tools available to AURA."""
    engine = _load_engine(ctx.obj["config"])
    console.print(engine.tool_registry.summary())


# ── version command ────────────────────────────────────────────────────────────

@main.command()
def version() -> None:
    """Print the AURA version."""
    from .. import __version__  # noqa: PLC0415
    console.print(f"AURA version [bold]{__version__}[/]")

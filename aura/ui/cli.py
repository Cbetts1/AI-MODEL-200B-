"""aura/ui/cli.py — Click-based CLI entry point.

Commands
--------
  aura chat               Interactive REPL chat with AURA.
  aura chat --once MSG    Send a single message and exit.
  aura serve              Start the HTTP/JSON API server (cloud-native).
  aura tools              List all available tools.
  aura templates          List all pre-fab templates.
  aura version            Print the AURA version.

The CLI reads config/aura.yaml (or the path set by --config) and builds an
AuraEngine automatically.

Usage
-----
    pip install -e .    # installs the `aura` command
    aura --help
    aura chat
    aura serve          # run AURA on the network
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

console = Console()

_DEFAULT_CONFIG = "config/aura.yaml"
_BANNER = "[bold cyan]AURA[/] — [dim]AI Unified Reasoning Architecture[/]  [bold]v0.3.0[/]"
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


def _load_raw_config(config_path: str) -> dict:
    """Return the raw dict from aura.yaml."""
    return yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}


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
@click.argument("message", default=None, required=False)
@click.option("--once", default=None, metavar="MESSAGE", help="Send one message and exit.")
@click.option("--session", default=None, metavar="ID", help="Resume a previous session by ID.")
@click.pass_context
def chat(ctx: click.Context, message: str | None, once: str | None, session: str | None) -> None:
    """Start an interactive chat session with AURA.

    Optionally pass MESSAGE as a positional argument to send a single message
    and exit (equivalent to --once).
    """
    config_path = ctx.obj["config"]
    engine = _load_engine(config_path)

    if session:
        engine.session.conversation_id = session
        engine.memory.load(engine.session)
        console.print(f"[dim]Resumed session {session}[/]")

    # Positional argument takes precedence over --once when both are supplied.
    # Click passes None (not "") for a missing optional argument, so `or` is safe here.
    one_shot = message or once
    if one_shot:
        reply = engine.chat(one_shot)
        _print_reply(reply, engine.persona.name)
        return

    # ── interactive REPL ───────────────────────────────────────────────────────
    console.print(Panel(_BANNER, border_style="cyan", padding=(0, 2)))
    console.print(
        f"[dim]Session ID: {engine.session.conversation_id}[/]\n"
        "[dim]Type 'exit' or Ctrl-C to quit.  "
        "/tool list to see tools.  "
        "/template list to see templates.[/]\n"
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

        if user_input.strip() == "/template list":
            console.print(engine.template_registry.summary())
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


# ── serve command ──────────────────────────────────────────────────────────────

@main.command()
@click.option("--host", default=None, help="Bind address (default from config or 0.0.0.0).")
@click.option("--port", default=None, type=int, help="Port number (default from config or 8000).")
@click.option("--token", default=None, metavar="TOKEN", help="Bearer token for auth (overrides config).")
@click.pass_context
def serve(ctx: click.Context, host: str | None, port: int | None, token: str | None) -> None:
    """Start the AURA HTTP/JSON API server.

    AURA is cloud-native — run it on any machine and access it from web
    pages, other servers, or any device on the network.  The web chat UI is
    served at the root URL (/).
    """
    config_path = ctx.obj["config"]
    engine = _load_engine(config_path)

    cfg = _load_raw_config(config_path)
    server_cfg = cfg.get("server", {})

    final_host = host or server_cfg.get("host", "0.0.0.0")
    final_port = port or server_cfg.get("port", 8000)
    # CLI flag > env var > config file
    final_token = token or os.environ.get("AURA_API_TOKEN") or server_cfg.get("api_token", "")

    from .api import run_server  # noqa: PLC0415
    run_server(engine, host=final_host, port=final_port, api_token=final_token)


# ── tools command ──────────────────────────────────────────────────────────────

@main.command(name="tools")
@click.pass_context
def list_tools(ctx: click.Context) -> None:
    """List all tools available to AURA."""
    engine = _load_engine(ctx.obj["config"])
    console.print(engine.tool_registry.summary())


# ── templates command ──────────────────────────────────────────────────────────

@main.command(name="templates")
@click.pass_context
def list_templates(ctx: click.Context) -> None:
    """List all pre-fab templates available to AURA."""
    engine = _load_engine(ctx.obj["config"])
    console.print(engine.template_registry.summary())


# ── version command ────────────────────────────────────────────────────────────

@main.command()
def version() -> None:
    """Print the AURA version."""
    from .. import __version__  # noqa: PLC0415
    console.print(f"AURA version [bold]{__version__}[/]")

"""aura/ui/api.py — Lightweight HTTP/JSON API server for AURA.

This module exposes AURA over HTTP so it can be accessed from web pages,
cloud servers, mobile apps, or any device on the network.  AURA is not
constrained to a single device — it travels where it is needed.

Endpoints
---------
  POST /v1/chat       Send a message and receive a reply.
  GET  /v1/health     Health-check / readiness probe.
  GET  /v1/tools      List available tools.
  GET  /v1/version    Return the AURA version string.

The server is built on Python's standard-library ``http.server`` so it has
**zero** extra dependencies.  For production deployments behind a reverse
proxy (nginx, Caddy, etc.) this is perfectly adequate; for high-concurrency
scenarios consider wrapping the :class:`AuraEngine` with a WSGI/ASGI
framework of your choice.

Usage
-----
    aura serve                      # start on 0.0.0.0:8000
    aura serve --port 9090          # custom port
    aura serve --host 127.0.0.1     # localhost only
"""

from __future__ import annotations

import json
import os
from functools import partial
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional

from ..core.engine import AuraEngine


# ── helpers ────────────────────────────────────────────────────────────────────

def _json_response(handler: BaseHTTPRequestHandler, status: int, body: dict) -> None:
    """Write a JSON response with proper headers."""
    payload = json.dumps(body).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    handler.end_headers()
    handler.wfile.write(payload)


def _read_json_body(handler: BaseHTTPRequestHandler) -> Optional[dict]:
    """Read and parse the JSON request body, or return *None* on error."""
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return None
    try:
        return json.loads(handler.rfile.read(length))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


# ── request handler ────────────────────────────────────────────────────────────

class AuraAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler that delegates to an :class:`AuraEngine`."""

    # Injected by the factory — see ``make_handler_class`` below.
    engine: AuraEngine
    api_token: str = ""

    # Silence per-request log lines (override for debugging).
    def log_message(self, fmt: str, *args: Any) -> None:  # pragma: no cover
        pass

    # ── auth ──────────────────────────────────────────────────────────────────

    def _check_auth(self) -> bool:
        """Return *True* if the request is authorised (or no token is set)."""
        if not self.api_token:
            return True
        auth = self.headers.get("Authorization", "")
        return auth == f"Bearer {self.api_token}"

    # ── CORS preflight ────────────────────────────────────────────────────────

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    # ── GET routes ────────────────────────────────────────────────────────────

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/v1/health":
            _json_response(self, HTTPStatus.OK, {"status": "ok"})
            return

        if self.path == "/v1/version":
            from .. import __version__  # noqa: PLC0415
            _json_response(self, HTTPStatus.OK, {"version": __version__})
            return

        if self.path == "/v1/tools":
            if not self._check_auth():
                _json_response(self, HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            tools = [
                {"name": n, "description": self.engine.tool_registry.get(n).description}
                for n in self.engine.tool_registry.list_tools()
            ]
            _json_response(self, HTTPStatus.OK, {"tools": tools})
            return

        _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})

    # ── POST routes ───────────────────────────────────────────────────────────

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/v1/chat":
            if not self._check_auth():
                _json_response(self, HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            body = _read_json_body(self)
            if body is None or "message" not in body:
                _json_response(
                    self,
                    HTTPStatus.BAD_REQUEST,
                    {"error": "request body must be JSON with a 'message' field"},
                )
                return
            reply = self.engine.chat(body["message"])
            _json_response(self, HTTPStatus.OK, {
                "reply": reply,
                "session_id": self.engine.session.conversation_id,
            })
            return

        _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})


# ── factory ────────────────────────────────────────────────────────────────────

def make_handler_class(engine: AuraEngine, api_token: str = "") -> type:
    """Return a handler class with *engine* and *api_token* baked in."""

    class _Handler(AuraAPIHandler):
        pass

    _Handler.engine = engine
    _Handler.api_token = api_token
    return _Handler


def run_server(
    engine: AuraEngine,
    host: str = "0.0.0.0",
    port: int = 8000,
    api_token: str = "",
) -> None:
    """Start the HTTP API server (blocks until interrupted)."""
    handler_cls = make_handler_class(engine, api_token=api_token)
    server = HTTPServer((host, port), handler_cls)
    print(f"AURA API server listening on http://{host}:{port}")
    print("Endpoints:")
    print(f"  POST http://{host}:{port}/v1/chat")
    print(f"  GET  http://{host}:{port}/v1/health")
    print(f"  GET  http://{host}:{port}/v1/tools")
    print(f"  GET  http://{host}:{port}/v1/version")
    print()
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()

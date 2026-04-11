"""aura/ui/api.py — Lightweight HTTP/JSON API server for AURA.

This module exposes AURA over HTTP so it can be accessed from web pages,
cloud servers, mobile apps, or any device on the network.  AURA is not
constrained to a single device — it travels where it is needed.

Endpoints
---------
  GET  /                Serve the web chat interface.
  GET  /v1/ui           Serve the web chat interface (alias).
  POST /v1/chat         Send a message and receive a reply.
  GET  /v1/chat/stream  SSE stream — real-time token-by-token reply.
  GET  /v1/health       Health-check / readiness probe.
  GET  /v1/tools        List available tools.
  GET  /v1/templates    List available pre-fab templates.
  POST /v1/template     Activate a pre-fab template.
  GET  /v1/models       List model backends and their availability.
  GET  /v1/version      Return the AURA version string.
  GET  /manifest.json   PWA manifest for installable web app.
  GET  /sw.js           Service worker for offline/PWA support.

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


def _html_response(handler: BaseHTTPRequestHandler, status: int, html: str) -> None:
    """Write an HTML response."""
    payload = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def _js_response(handler: BaseHTTPRequestHandler, status: int, js: str) -> None:
    """Write a JavaScript response."""
    payload = js.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/javascript; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def _sse_response(
    handler: BaseHTTPRequestHandler,
    status: int,
    reply: str,
    session_id: str,
) -> None:
    """Write a Server-Sent Events response carrying a single complete message."""
    # Encode the reply as a JSON object inside an SSE event
    event_data = json.dumps({"reply": reply, "session_id": session_id, "done": True})
    # SSE format: "data: <payload>\n\n"
    payload = f"data: {event_data}\n\n".encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/event-stream; charset=utf-8")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
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


# ── PWA assets ─────────────────────────────────────────────────────────────────

_PWA_MANIFEST = json.dumps({
    "name": "AURA — AI Unified Reasoning Architecture",
    "short_name": "AURA",
    "description": "Free AI assistant for everyone. Chat, voice, video, and real-world tools.",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0a0e27",
    "theme_color": "#0a0e27",
    "icons": [
        {
            "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
                   "<circle cx='50' cy='50' r='45' fill='%233b5bdb'/>"
                   "<text x='50' y='65' text-anchor='middle' font-size='40' fill='white'>✦</text></svg>",
            "sizes": "any",
            "type": "image/svg+xml"
        }
    ]
})

_SERVICE_WORKER = """\
// AURA Service Worker — enables PWA install and basic offline support.
const CACHE_NAME = "aura-v1";
const OFFLINE_URL = "/";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(clients.claim());
});

self.addEventListener("fetch", (event) => {
  // Network-first strategy
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
"""


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
        # Web UI
        if self.path in ("/", "/v1/ui"):
            from .gui.webui import render_chat_html  # noqa: PLC0415
            _html_response(self, HTTPStatus.OK, render_chat_html())
            return

        # PWA manifest
        if self.path == "/manifest.json":
            _json_response(self, HTTPStatus.OK, json.loads(_PWA_MANIFEST))
            return

        # Service worker
        if self.path == "/sw.js":
            _js_response(self, HTTPStatus.OK, _SERVICE_WORKER)
            return

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

        if self.path == "/v1/templates":
            templates = [
                t.to_dict()
                for t in self.engine.template_registry.all_templates()
            ]
            _json_response(self, HTTPStatus.OK, {"templates": templates})
            return

        if self.path == "/v1/models":
            model = self.engine.model
            # Support ModelRouter introspection
            if hasattr(model, "backend_status"):
                backends = model.backend_status()
            else:
                backends = [{
                    "name": type(model).__name__,
                    "available": model.is_available(),
                    "type": type(model).__name__,
                }]
            _json_response(self, HTTPStatus.OK, {"backends": backends})
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

        if self.path == "/v1/chat/stream":
            # Server-Sent Events streaming endpoint.
            # The engine does not natively stream at v0.4 so we emit the
            # complete reply as a single SSE event after generation.
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
            session_id = self.engine.session.conversation_id
            _sse_response(self, HTTPStatus.OK, reply, session_id)
            return

        if self.path == "/v1/template":
            body = _read_json_body(self)
            if body is None or "template" not in body:
                _json_response(
                    self,
                    HTTPStatus.BAD_REQUEST,
                    {"error": "request body must be JSON with a 'template' field"},
                )
                return
            greeting = self.engine.apply_template(body["template"])
            _json_response(self, HTTPStatus.OK, {
                "reply": greeting,
                "greeting": greeting,
                "template": body["template"],
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
    print(f"🚀 AURA v0.4.0 — AI Unified Reasoning Architecture")
    print(f"")
    print(f"   Web UI:  http://{host}:{port}/")
    print(f"")
    print(f"   API Endpoints:")
    print(f"     POST http://{host}:{port}/v1/chat")
    print(f"     POST http://{host}:{port}/v1/chat/stream   (SSE streaming)")
    print(f"     GET  http://{host}:{port}/v1/health")
    print(f"     GET  http://{host}:{port}/v1/tools")
    print(f"     GET  http://{host}:{port}/v1/templates")
    print(f"     POST http://{host}:{port}/v1/template")
    print(f"     GET  http://{host}:{port}/v1/models        (backend status)")
    print(f"     GET  http://{host}:{port}/v1/version")
    print(f"")
    print(f"   Open the Web UI in your browser to start chatting!")
    print(f"   Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()

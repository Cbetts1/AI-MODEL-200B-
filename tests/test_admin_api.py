"""tests/test_admin_api.py — Unit tests for the AURA Admin API (v0.5.0)."""

import json
import io
import email
from http import HTTPStatus
from unittest.mock import MagicMock

import pytest

from aura.ui.api import AuraAPIHandler, make_handler_class, _json_response
from aura.ui.admin import (
    get_system_status,
    get_log_lines,
    render_admin_html,
    log as admin_log,
    _RESTART_REQUESTED,
    _LOG_BUFFER,
    clear_restart_flag,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_engine():
    engine = MagicMock()
    engine.chat.return_value = "Hello from AURA"
    engine.session.conversation_id = "test-session-123"
    engine.tool_registry.list_tools.return_value = ["shell"]
    shell_tool = MagicMock()
    shell_tool.description = "Run shell commands"
    engine.tool_registry.get.return_value = shell_tool

    # Model with backend_status
    model = MagicMock()
    model.is_available.return_value = True
    model.backend_status.return_value = [
        {"name": "groq", "available": True, "type": "RemoteModel"},
        {"name": "echo", "available": True, "type": "EchoModel"},
    ]
    engine.model = model
    return engine


def _make_handler(engine, method, path, body=None, headers=None,
                  api_token="", admin_token=""):
    handler_cls = make_handler_class(engine, api_token=api_token, admin_token=admin_token)
    body_bytes = json.dumps(body).encode("utf-8") if body else b""
    header_lines = f"Host: localhost\r\nContent-Length: {len(body_bytes)}\r\n"
    if headers:
        for k, v in headers.items():
            header_lines += f"{k}: {v}\r\n"
    handler = handler_cls.__new__(handler_cls)
    handler.rfile = io.BytesIO(body_bytes)
    handler.wfile = io.BytesIO()
    handler.client_address = ("127.0.0.1", 0)
    handler.requestline = f"{method} {path} HTTP/1.1"
    handler.command = method
    handler.path = path
    handler.headers = email.message_from_string(header_lines)
    handler.request_version = "HTTP/1.1"
    handler.close_connection = True
    return handler


# ── Admin module unit tests ────────────────────────────────────────────────────

class TestAdminModule:
    def test_admin_log_appends(self):
        _LOG_BUFFER.clear()
        admin_log("test message")
        lines = get_log_lines(10)
        assert any("test message" in l for l in lines)

    def test_get_log_lines_limit(self):
        _LOG_BUFFER.clear()
        for i in range(20):
            admin_log(f"line {i}")
        lines = get_log_lines(5)
        assert len(lines) == 5

    def test_get_log_lines_all(self):
        _LOG_BUFFER.clear()
        for i in range(10):
            admin_log(f"msg {i}")
        lines = get_log_lines(100)
        assert len(lines) == 10

    def test_get_system_status_returns_dict(self):
        engine = _make_engine()
        status = get_system_status(engine)
        assert isinstance(status, dict)
        assert "version" in status
        assert "uptime" in status
        assert "memory" in status
        assert "model_backends" in status

    def test_get_system_status_no_engine(self):
        status = get_system_status(None)
        assert isinstance(status, dict)
        assert status["model_backends"] == []

    def test_render_admin_html_contains_keywords(self):
        html = render_admin_html()
        assert "AURA Admin" in html
        assert "admin-token" in html
        assert "/admin/status" in html

    def test_restart_flag(self):
        _RESTART_REQUESTED.clear()
        assert not _RESTART_REQUESTED.is_set()
        _RESTART_REQUESTED.set()
        assert _RESTART_REQUESTED.is_set()
        clear_restart_flag()
        assert not _RESTART_REQUESTED.is_set()


# ── Admin API endpoint tests ───────────────────────────────────────────────────

ADMIN_TOKEN = "test-admin-secret"
ADMIN_AUTH = {"Authorization": f"Bearer {ADMIN_TOKEN}"}


class TestAdminEndpointsDisabled:
    """Admin endpoints must return 503 when no admin_token is configured."""

    def _get(self, path):
        engine = _make_engine()
        h = _make_handler(engine, "GET", path, admin_token="")
        h.do_GET()
        h.wfile.seek(0)
        return h.wfile.read()

    def _post(self, path):
        engine = _make_engine()
        h = _make_handler(engine, "POST", path, body={}, admin_token="")
        h.do_POST()
        h.wfile.seek(0)
        return h.wfile.read()

    def test_admin_dashboard_disabled(self):
        assert b"disabled" in self._get("/admin")

    def test_admin_status_disabled(self):
        assert b"disabled" in self._get("/admin/status")

    def test_admin_logs_disabled(self):
        assert b"disabled" in self._get("/admin/logs")

    def test_admin_cloud_disabled(self):
        assert b"disabled" in self._get("/admin/cloud")

    def test_admin_restart_disabled(self):
        assert b"disabled" in self._post("/admin/restart")

    def test_admin_config_disabled(self):
        assert b"disabled" in self._post("/admin/config")

    def test_admin_cloud_connect_disabled(self):
        assert b"disabled" in self._post("/admin/cloud/connect")


class TestAdminEndpointsUnauthorized:
    """Admin endpoints must return 401 when wrong/missing token."""

    def _get(self, path):
        engine = _make_engine()
        h = _make_handler(engine, "GET", path, admin_token=ADMIN_TOKEN)
        h.do_GET()
        h.wfile.seek(0)
        return h.wfile.read()

    def _post(self, path):
        engine = _make_engine()
        h = _make_handler(engine, "POST", path, body={}, admin_token=ADMIN_TOKEN)
        h.do_POST()
        h.wfile.seek(0)
        return h.wfile.read()

    def test_admin_dashboard_unauthorized(self):
        assert b"unauthorized" in self._get("/admin")

    def test_admin_status_unauthorized(self):
        assert b"unauthorized" in self._get("/admin/status")

    def test_admin_logs_unauthorized(self):
        assert b"unauthorized" in self._get("/admin/logs")

    def test_admin_cloud_unauthorized(self):
        assert b"unauthorized" in self._get("/admin/cloud")

    def test_admin_restart_unauthorized(self):
        assert b"unauthorized" in self._post("/admin/restart")

    def test_admin_config_unauthorized(self):
        assert b"unauthorized" in self._post("/admin/config")

    def test_admin_cloud_connect_unauthorized(self):
        assert b"unauthorized" in self._post("/admin/cloud/connect")


class TestAdminEndpointsAuthorized:
    """Admin endpoints must work correctly when the correct token is provided."""

    def _get(self, path, extra_headers=None):
        engine = _make_engine()
        hdrs = {**ADMIN_AUTH, **(extra_headers or {})}
        h = _make_handler(engine, "GET", path, headers=hdrs, admin_token=ADMIN_TOKEN)
        h.do_GET()
        h.wfile.seek(0)
        return h.wfile.read()

    def _post(self, path, body=None):
        engine = _make_engine()
        h = _make_handler(
            engine, "POST", path,
            body=body or {},
            headers=ADMIN_AUTH,
            admin_token=ADMIN_TOKEN,
        )
        h.do_POST()
        h.wfile.seek(0)
        return h.wfile.read()

    def test_admin_dashboard_returns_html(self):
        out = self._get("/admin")
        assert b"AURA Admin" in out

    def test_admin_dashboard_trailing_slash(self):
        engine = _make_engine()
        h = _make_handler(engine, "GET", "/admin/", headers=ADMIN_AUTH, admin_token=ADMIN_TOKEN)
        h.do_GET()
        h.wfile.seek(0)
        assert b"AURA Admin" in h.wfile.read()

    def test_admin_status_returns_json(self):
        out = self._get("/admin/status")
        assert b"version" in out
        assert b"uptime" in out
        assert b"memory" in out

    def test_admin_status_has_backends(self):
        out = self._get("/admin/status")
        assert b"model_backends" in out

    def test_admin_logs_returns_lines(self):
        _LOG_BUFFER.clear()
        admin_log("test admin log entry")
        out = self._get("/admin/logs")
        assert b"lines" in out

    def test_admin_logs_query_param(self):
        out = self._get("/admin/logs?n=5")
        assert b"lines" in out
        assert b'"count": 5' in out or b'"count":5' in out

    def test_admin_cloud_returns_backends(self):
        out = self._get("/admin/cloud")
        assert b"cloud_backends" in out

    def test_admin_restart_sets_flag(self):
        _RESTART_REQUESTED.clear()
        out = self._post("/admin/restart")
        assert b"restart" in out.lower()
        assert _RESTART_REQUESTED.is_set()
        clear_restart_flag()

    def test_admin_config_returns_message(self):
        out = self._post("/admin/config", {"reload": True})
        assert b"message" in out

    def test_admin_cloud_connect_returns_status(self):
        out = self._post("/admin/cloud/connect")
        assert b"message" in out or b"backends" in out


class TestMakeHandlerClassAdminToken:
    def test_admin_token_injected(self):
        engine = _make_engine()
        cls = make_handler_class(engine, api_token="tok", admin_token="admin-tok")
        assert cls.admin_token == "admin-tok"
        assert cls.api_token == "tok"

    def test_default_admin_token_empty(self):
        engine = _make_engine()
        cls = make_handler_class(engine)
        assert cls.admin_token == ""

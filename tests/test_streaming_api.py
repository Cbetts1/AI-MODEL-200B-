"""tests/test_streaming_api.py — Tests for the SSE streaming endpoint (v0.4.0)."""

from __future__ import annotations

import io
import json
from http import HTTPStatus
from unittest.mock import MagicMock

import pytest

from aura.ui.api import (
    AuraAPIHandler,
    make_handler_class,
    _sse_response,
    _json_response,
)


# ── Helpers (reused from test_api.py pattern) ─────────────────────────────────

def _make_engine():
    engine = MagicMock()
    engine.chat.return_value = "Streaming reply from AURA"
    engine.session.conversation_id = "stream-session-1"
    engine.tool_registry.list_tools.return_value = ["shell"]
    shell_tool = MagicMock()
    shell_tool.description = "Run shell"
    engine.tool_registry.get.return_value = shell_tool

    # Mock model with backend_status (router-style)
    engine.model.backend_status.return_value = [
        {"name": "groq", "available": True, "type": "RemoteModelBackend"},
        {"name": "echo", "available": True, "type": "EchoModelBackend"},
    ]
    engine.model.is_available.return_value = True
    return engine


class _FakeWfile(io.BytesIO):
    pass


def _make_handler(engine, method, path, body=None, headers=None, api_token=""):
    handler_cls = make_handler_class(engine, api_token=api_token)
    body_bytes = json.dumps(body).encode("utf-8") if body else b""
    request_line = f"{method} {path} HTTP/1.1\r\n"
    header_lines = f"Host: localhost\r\nContent-Length: {len(body_bytes)}\r\n"
    if headers:
        for k, v in headers.items():
            header_lines += f"{k}: {v}\r\n"
    raw = (request_line + header_lines + "\r\n").encode("utf-8") + body_bytes

    handler = handler_cls.__new__(handler_cls)
    handler.rfile = io.BytesIO(raw)
    handler.wfile = _FakeWfile()
    handler.connection = MagicMock()
    handler.client_address = ("127.0.0.1", 1234)
    handler.server = MagicMock()
    handler.handle_one_request()
    return handler


def _get_response_body(handler) -> bytes:
    handler.wfile.seek(0)
    raw = handler.wfile.read()
    # HTTP response is: status line + headers + blank line + body
    if b"\r\n\r\n" in raw:
        return raw.split(b"\r\n\r\n", 1)[1]
    return raw


def _get_status_code(handler) -> int:
    handler.wfile.seek(0)
    line = handler.wfile.read().split(b"\r\n", 1)[0]
    return int(line.split(b" ")[1])


# ── /v1/chat/stream tests ─────────────────────────────────────────────────────

class TestStreamEndpoint:

    def test_stream_returns_200(self):
        engine = _make_engine()
        handler = _make_handler(engine, "POST", "/v1/chat/stream", {"message": "hello"})
        assert _get_status_code(handler) == HTTPStatus.OK

    def test_stream_content_type_is_sse(self):
        engine = _make_engine()
        handler = _make_handler(engine, "POST", "/v1/chat/stream", {"message": "hello"})
        handler.wfile.seek(0)
        raw = handler.wfile.read().decode("utf-8", errors="replace")
        assert "text/event-stream" in raw

    def test_stream_body_contains_sse_data(self):
        engine = _make_engine()
        handler = _make_handler(engine, "POST", "/v1/chat/stream", {"message": "test"})
        body = _get_response_body(handler).decode("utf-8", errors="replace")
        assert body.startswith("data: ")

    def test_stream_body_is_valid_json(self):
        engine = _make_engine()
        handler = _make_handler(engine, "POST", "/v1/chat/stream", {"message": "test"})
        body = _get_response_body(handler).decode("utf-8", errors="replace")
        # Extract JSON from SSE "data: {...}"
        for line in body.splitlines():
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                assert "reply" in payload
                assert "session_id" in payload
                assert "done" in payload
                assert payload["done"] is True
                return
        pytest.fail("No SSE data line found in response body")

    def test_stream_reply_content(self):
        engine = _make_engine()
        engine.chat.return_value = "Hello from streaming AURA"
        handler = _make_handler(engine, "POST", "/v1/chat/stream", {"message": "hi"})
        body = _get_response_body(handler).decode("utf-8", errors="replace")
        for line in body.splitlines():
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                assert payload["reply"] == "Hello from streaming AURA"
                return
        pytest.fail("Reply not found in SSE body")

    def test_stream_missing_message_returns_400(self):
        engine = _make_engine()
        handler = _make_handler(engine, "POST", "/v1/chat/stream", {"other": "field"})
        assert _get_status_code(handler) == HTTPStatus.BAD_REQUEST

    def test_stream_empty_body_returns_400(self):
        engine = _make_engine()
        handler = _make_handler(engine, "POST", "/v1/chat/stream", None)
        assert _get_status_code(handler) == HTTPStatus.BAD_REQUEST

    def test_stream_calls_engine_chat(self):
        engine = _make_engine()
        _make_handler(engine, "POST", "/v1/chat/stream", {"message": "ping"})
        engine.chat.assert_called_once_with("ping")


# ── /v1/models tests ──────────────────────────────────────────────────────────

class TestModelsEndpoint:

    def test_models_returns_200(self):
        engine = _make_engine()
        handler = _make_handler(engine, "GET", "/v1/models")
        assert _get_status_code(handler) == HTTPStatus.OK

    def test_models_returns_backends_list(self):
        engine = _make_engine()
        handler = _make_handler(engine, "GET", "/v1/models")
        body = json.loads(_get_response_body(handler))
        assert "backends" in body
        assert isinstance(body["backends"], list)

    def test_models_backend_has_required_fields(self):
        engine = _make_engine()
        handler = _make_handler(engine, "GET", "/v1/models")
        body = json.loads(_get_response_body(handler))
        for backend in body["backends"]:
            assert "name" in backend
            assert "available" in backend

    def test_models_router_backend_status(self):
        engine = _make_engine()
        handler = _make_handler(engine, "GET", "/v1/models")
        body = json.loads(_get_response_body(handler))
        names = [b["name"] for b in body["backends"]]
        assert "groq" in names
        assert "echo" in names

    def test_models_non_router_fallback(self):
        engine = _make_engine()
        # Remove backend_status to simulate non-router model
        del engine.model.backend_status
        engine.model.is_available.return_value = True
        handler = _make_handler(engine, "GET", "/v1/models")
        assert _get_status_code(handler) == HTTPStatus.OK
        body = json.loads(_get_response_body(handler))
        assert len(body["backends"]) >= 1


# ── _sse_response helper ──────────────────────────────────────────────────────

class TestSseResponseHelper:

    def test_sse_response_writes_event_stream(self):
        mock_handler = MagicMock()
        mock_handler.wfile = io.BytesIO()
        mock_handler.send_response = MagicMock()
        mock_handler.send_header = MagicMock()
        mock_handler.end_headers = MagicMock()

        _sse_response(mock_handler, HTTPStatus.OK, "test reply", "sess-123")

        # Check Content-Type header was set
        header_calls = [str(c) for c in mock_handler.send_header.call_args_list]
        assert any("event-stream" in c for c in header_calls)

    def test_sse_response_data_format(self):
        captured_bytes = []

        class _FakeHandler:
            def send_response(self, _): pass
            def send_header(self, k, v): pass
            def end_headers(self): pass

            class wfile:
                @staticmethod
                def write(b): captured_bytes.append(b)

        _sse_response(_FakeHandler(), HTTPStatus.OK, "hello world", "s1")
        payload = b"".join(captured_bytes).decode()
        assert payload.startswith("data: ")
        data = json.loads(payload[6:].strip())
        assert data["reply"] == "hello world"
        assert data["session_id"] == "s1"
        assert data["done"] is True

"""Tests for the web chat interface and new API endpoints."""

import json
import threading
from http import HTTPStatus
from http.server import HTTPServer
from io import BytesIO

from aura.core.engine import AuraEngine
from aura.model.dummy import EchoModelBackend
from aura.identity.persona import Persona
from aura.ui.api import AuraAPIHandler, make_handler_class
from aura.ui.gui.webui import render_chat_html


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_engine():
    """Create a test engine with echo backend."""
    return AuraEngine(
        model=EchoModelBackend(),
        persona=Persona(),
    )


class FakeHTTPRequest:
    """Minimal fake for testing the handler without a real socket."""

    def __init__(self, method, path, body=None, headers=None):
        self.method = method
        self.path = path
        self.body = body or b""
        self.headers_dict = headers or {}

    def makefile(self, mode, *args, **kwargs):
        if "b" in mode:
            if self.method == "POST":
                request_line = f"{self.method} {self.path} HTTP/1.1\r\n"
                header_lines = f"Content-Length: {len(self.body)}\r\n"
                for k, v in self.headers_dict.items():
                    header_lines += f"{k}: {v}\r\n"
                header_lines += "\r\n"
                return BytesIO(
                    request_line.encode() + header_lines.encode() + self.body
                )
            else:
                request_line = f"{self.method} {self.path} HTTP/1.1\r\n\r\n"
                return BytesIO(request_line.encode())
        return BytesIO()


class TestRenderChatHTML:
    """Test that the chat HTML is generated correctly."""

    def test_returns_html(self):
        html = render_chat_html()
        assert "<!DOCTYPE html>" in html
        assert "AURA" in html

    def test_contains_chat_elements(self):
        html = render_chat_html()
        assert "message-input" in html
        assert "send-btn" in html
        assert "messages-area" in html

    def test_contains_template_section(self):
        html = render_chat_html()
        assert "template-list" in html
        assert "Quick Templates" in html

    def test_contains_comm_buttons(self):
        html = render_chat_html()
        assert "btn-voice" in html
        assert "btn-video" in html
        assert "btn-screen" in html

    def test_contains_theme_toggle(self):
        html = render_chat_html()
        assert "theme-toggle" in html
        assert "toggleTheme" in html

    def test_api_base_replacement(self):
        html = render_chat_html(api_base="http://example.com")
        assert "http://example.com" in html

    def test_responsive_design(self):
        html = render_chat_html()
        assert "@media" in html
        assert "768px" in html

    def test_welcome_screen(self):
        html = render_chat_html()
        assert "welcome-screen" in html
        assert "Welcome to AURA" in html

    def test_pwa_manifest_link(self):
        html = render_chat_html()
        assert "manifest.json" in html

    def test_service_worker_registration(self):
        html = render_chat_html()
        assert "serviceWorker" in html


class TestNewAPIEndpoints:
    """Test the new API endpoints (templates, web UI, PWA)."""

    def test_make_handler_class_with_engine(self):
        engine = _make_engine()
        cls = make_handler_class(engine)
        assert cls.engine is engine

    def test_engine_has_template_registry(self):
        engine = _make_engine()
        assert engine.template_registry is not None
        assert len(engine.template_registry.list_templates()) >= 10

    def test_apply_template(self):
        engine = _make_engine()
        greeting = engine.apply_template("code_helper")
        assert "Code Helper" in greeting
        assert engine.active_template == "code_helper"

    def test_apply_unknown_template(self):
        engine = _make_engine()
        result = engine.apply_template("nonexistent")
        assert "Unknown" in result

    def test_template_command_list(self):
        engine = _make_engine()
        result = engine.chat("/template list")
        assert "code_helper" in result.lower() or "Code Helper" in result

    def test_template_command_use(self):
        engine = _make_engine()
        result = engine.chat("/template use code_helper")
        assert "Code Helper" in result

    def test_template_command_reset(self):
        engine = _make_engine()
        engine.apply_template("code_helper")
        result = engine.chat("/template reset")
        assert "reset" in result.lower()
        assert engine.active_template is None

    def test_engine_reset_clears_template(self):
        engine = _make_engine()
        engine.apply_template("code_helper")
        engine.reset()
        assert engine.active_template is None

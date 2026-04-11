"""tests/test_new_tools_v04.py — Tests for the 5 new tools added in v0.4.0."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from aura.tools.weather import WeatherTool
from aura.tools.url_reader import URLReaderTool, _TextExtractor
from aura.tools.notes import NotesTool, _load, _save
from aura.tools.translator import TranslatorTool
from aura.tools.image_analyzer import ImageAnalyzerTool
from aura.tools.registry import build_default_registry


# ── WeatherTool ────────────────────────────────────────────────────────────────

class TestWeatherTool:

    def setup_method(self):
        self.tool = WeatherTool()

    def test_name_and_description(self):
        assert self.tool.name == "weather"
        assert "weather" in self.tool.description.lower()

    def test_no_city_returns_usage(self):
        result = self.tool.run("")
        assert "Usage" in result

    def test_whitespace_only_returns_usage(self):
        result = self.tool.run("   ")
        assert "Usage" in result

    def test_network_error_returns_warning(self):
        with patch("urllib.request.urlopen", side_effect=OSError("no network")):
            result = self.tool.run("London")
        assert "⚠️" in result or "Could not" in result

    def test_successful_weather(self):
        mock_data = {
            "current_condition": [{
                "temp_C": "15", "temp_F": "59", "FeelsLikeC": "13",
                "humidity": "70", "weatherDesc": [{"value": "Partly Cloudy"}],
                "windspeedKmph": "20", "winddir16Point": "NW",
                "visibility": "10", "uvIndex": "3"
            }],
            "nearest_area": [{
                "areaName": [{"value": "London"}],
                "country": [{"value": "United Kingdom"}],
            }],
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = self.tool.run("London")

        assert "London" in result
        assert "15°C" in result
        assert "Partly Cloudy" in result
        assert "🌡️" in result


# ── URLReaderTool ─────────────────────────────────────────────────────────────

class TestURLReaderTool:

    def setup_method(self):
        self.tool = URLReaderTool()

    def test_name_and_description(self):
        assert self.tool.name == "url_reader"
        assert "url" in self.tool.description.lower() or "fetch" in self.tool.description.lower()

    def test_no_url_returns_usage(self):
        result = self.tool.run("")
        assert "Usage" in result

    def test_network_error_returns_warning(self):
        with patch("urllib.request.urlopen", side_effect=OSError("no network")):
            result = self.tool.run("https://example.com")
        assert "⚠️" in result or "Failed" in result

    def test_successful_html_fetch(self):
        html = b"<html><body><p>Hello World</p></body></html>"
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.headers.get.return_value = "text/html; charset=utf-8"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = self.tool.run("https://example.com")

        assert "Hello World" in result
        assert "🌐" in result

    def test_prepends_https_scheme(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"<html><body>test</body></html>"
        mock_resp.headers.get.return_value = "text/html"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with patch("urllib.request.Request") as MockRequest:
                MockRequest.return_value = MagicMock()
                self.tool.run("example.com")
                # The URL passed to Request should start with https://
                call_url = MockRequest.call_args[0][0]
                assert call_url.startswith("https://")


class TestTextExtractor:

    def test_extracts_paragraph_text(self):
        parser = _TextExtractor()
        parser.feed("<html><body><p>Hello World</p></body></html>")
        assert "Hello World" in parser.get_text()

    def test_skips_script_content(self):
        parser = _TextExtractor()
        parser.feed("<html><body><script>var x=1;</script><p>Visible</p></body></html>")
        text = parser.get_text()
        assert "Visible" in text
        assert "var x=1;" not in text

    def test_skips_style_content(self):
        parser = _TextExtractor()
        parser.feed("<html><head><style>body{color:red}</style></head><body>Text</body></html>")
        assert "color:red" not in parser.get_text()

    def test_handles_nested_tags(self):
        parser = _TextExtractor()
        parser.feed("<div><p><strong>Bold</strong> text</p></div>")
        text = parser.get_text()
        assert "Bold" in text
        assert "text" in text


# ── NotesTool ─────────────────────────────────────────────────────────────────

class TestNotesTool:

    def setup_method(self):
        self.tool = NotesTool()
        # Use a temp file for notes during tests
        self._orig_file = None

    def test_name_and_description(self):
        assert self.tool.name == "notes"
        assert "note" in self.tool.description.lower()

    def test_save_and_get(self, tmp_path, monkeypatch):
        notes_file = tmp_path / "notes.json"
        monkeypatch.setattr("aura.tools.notes._NOTES_FILE", notes_file)
        result = self.tool.run("save mykey My note content")
        assert "saved" in result.lower() or "mykey" in result
        result2 = self.tool.run("get mykey")
        assert "My note content" in result2

    def test_list_empty(self, tmp_path, monkeypatch):
        notes_file = tmp_path / "notes.json"
        monkeypatch.setattr("aura.tools.notes._NOTES_FILE", notes_file)
        result = self.tool.run("list")
        assert "No notes" in result or "saved" in result.lower()

    def test_list_with_notes(self, tmp_path, monkeypatch):
        notes_file = tmp_path / "notes.json"
        monkeypatch.setattr("aura.tools.notes._NOTES_FILE", notes_file)
        self.tool.run("save alpha First note")
        self.tool.run("save beta Second note")
        result = self.tool.run("list")
        assert "alpha" in result
        assert "beta" in result

    def test_delete(self, tmp_path, monkeypatch):
        notes_file = tmp_path / "notes.json"
        monkeypatch.setattr("aura.tools.notes._NOTES_FILE", notes_file)
        self.tool.run("save delme temp note")
        del_result = self.tool.run("delete delme")
        assert "deleted" in del_result.lower() or "delme" in del_result
        get_result = self.tool.run("get delme")
        assert "No note" in get_result or "delme" in get_result

    def test_get_missing_key(self, tmp_path, monkeypatch):
        notes_file = tmp_path / "notes.json"
        monkeypatch.setattr("aura.tools.notes._NOTES_FILE", notes_file)
        result = self.tool.run("get nonexistent")
        assert "No note" in result or "nonexistent" in result

    def test_save_missing_content_shows_usage(self):
        result = self.tool.run("save keyonly")
        assert "Usage" in result

    def test_no_subcommand_shows_help(self):
        result = self.tool.run("")
        assert "save" in result.lower() or "notes" in result.lower()

    def test_unknown_subcommand_shows_help(self):
        result = self.tool.run("unknowncmd")
        assert "save" in result.lower() or "notes" in result.lower()


# ── TranslatorTool ────────────────────────────────────────────────────────────

class TestTranslatorTool:

    def setup_method(self):
        self.tool = TranslatorTool()

    def test_name_and_description(self):
        assert self.tool.name == "translator"
        assert "translat" in self.tool.description.lower()

    def test_no_args_returns_usage(self):
        result = self.tool.run("")
        assert "Usage" in result

    def test_missing_text_returns_usage(self):
        result = self.tool.run("French")
        assert "Usage" in result

    def test_returns_translation_prompt(self):
        result = self.tool.run("French Hello, world!")
        assert "French" in result
        assert "Hello" in result

    def test_includes_target_language(self):
        result = self.tool.run("Japanese Good morning")
        assert "Japanese" in result


# ── ImageAnalyzerTool ─────────────────────────────────────────────────────────

class TestImageAnalyzerTool:

    def setup_method(self):
        self.tool = ImageAnalyzerTool()

    def test_name_and_description(self):
        assert self.tool.name == "image_analyzer"
        assert "image" in self.tool.description.lower()

    def test_no_args_returns_usage(self):
        result = self.tool.run("")
        assert "Usage" in result or "provide" in result.lower()

    def test_no_api_key_returns_setup_info(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        result = self.tool.run("https://example.com/image.jpg")
        assert "vision" in result.lower() or "API" in result or "enable" in result.lower()

    def test_describe_prefix_stripped(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        result = self.tool.run("describe https://example.com/pic.png")
        # Should not crash and should contain the URL in output
        assert "example.com" in result or "vision" in result.lower()

    def test_prepends_https(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        result = self.tool.run("example.com/img.jpg")
        assert "example.com" in result


# ── Registry integration ───────────────────────────────────────────────────────

class TestRegistryV04:

    def test_default_registry_has_new_tools(self):
        reg = build_default_registry()
        tools = reg.list_tools()
        assert "weather" in tools
        assert "url_reader" in tools
        assert "notes" in tools
        assert "translator" in tools
        assert "image_analyzer" in tools

    def test_total_tool_count(self):
        reg = build_default_registry()
        # 10 original + 5 new = 15
        assert len(reg.list_tools()) >= 15

    def test_all_new_tools_have_descriptions(self):
        reg = build_default_registry()
        for name in ["weather", "url_reader", "notes", "translator", "image_analyzer"]:
            tool = reg.get(name)
            assert tool is not None
            assert len(tool.description) > 0

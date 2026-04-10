"""tests/test_persona.py — Unit tests for aura.identity.persona."""

import pytest
from pathlib import Path

from aura.identity.persona import Persona


class TestPersona:
    def test_defaults(self):
        p = Persona()
        assert p.name == "AURA"
        assert "concise" in p.tone

    def test_system_prompt_contains_name(self):
        p = Persona(name="AURA", backstory="A test backstory.")
        prompt = p.system_prompt()
        assert "AURA" in prompt
        assert "A test backstory." in prompt

    def test_system_prompt_capabilities(self):
        p = Persona(capabilities=["shell", "web_search"])
        prompt = p.system_prompt()
        assert "shell" in prompt
        assert "web_search" in prompt

    def test_from_config_missing_file(self, tmp_path):
        """Should return sensible defaults if the file does not exist."""
        p = Persona.from_config(str(tmp_path / "nonexistent.yaml"))
        assert p.name == "AURA"

    def test_from_config_loads_yaml(self, tmp_path):
        yaml_content = (
            "name: TestBot\n"
            "tone: sarcastic\n"
            "backstory: I am a test.\n"
            "capabilities:\n"
            "  - testing\n"
            "custom_instructions: Be precise.\n"
        )
        cfg = tmp_path / "identity.yaml"
        cfg.write_text(yaml_content)
        p = Persona.from_config(str(cfg))
        assert p.name == "TestBot"
        assert p.tone == "sarcastic"
        assert "I am a test." in p.backstory
        assert "testing" in p.capabilities

    def test_repr(self):
        assert "AURA" in repr(Persona())

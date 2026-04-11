"""Tests for the pre-fab template system."""

import pytest

from aura.templates.registry import (
    Template,
    TemplateRegistry,
    build_default_template_registry,
)


class TestTemplate:
    def test_to_dict(self):
        t = Template(
            name="test",
            title="Test Template",
            description="A test template.",
            icon="🧪",
            system_prompt_overlay="You are a test bot.",
            greeting="Hello from test!",
            tags=["test"],
        )
        d = t.to_dict()
        assert d["name"] == "test"
        assert d["title"] == "Test Template"
        assert d["icon"] == "🧪"
        assert d["tags"] == ["test"]
        # system_prompt_overlay should NOT be in the dict (it's internal)
        assert "system_prompt_overlay" not in d

    def test_default_fields(self):
        t = Template(
            name="x", title="X", description="d", icon="✦",
            system_prompt_overlay="o", greeting="g",
        )
        assert t.suggested_tools == []
        assert t.tags == []


class TestTemplateRegistry:
    def test_register_and_get(self):
        reg = TemplateRegistry()
        t = Template(
            name="alpha", title="Alpha", description="d", icon="A",
            system_prompt_overlay="o", greeting="g",
        )
        reg.register(t)
        assert reg.get("alpha") is t

    def test_get_missing(self):
        reg = TemplateRegistry()
        assert reg.get("nope") is None

    def test_list_templates(self):
        reg = TemplateRegistry()
        for name in ("beta", "alpha", "gamma"):
            reg.register(Template(
                name=name, title=name.title(), description="d", icon="X",
                system_prompt_overlay="o", greeting="g",
            ))
        assert reg.list_templates() == ["alpha", "beta", "gamma"]

    def test_all_templates(self):
        reg = TemplateRegistry()
        reg.register(Template(
            name="one", title="One", description="d", icon="1",
            system_prompt_overlay="o", greeting="g",
        ))
        all_t = reg.all_templates()
        assert len(all_t) == 1
        assert all_t[0].name == "one"

    def test_summary_contains_names(self):
        reg = build_default_template_registry()
        summary = reg.summary()
        assert "code_helper" in summary
        assert "writing_assistant" in summary
        assert "math_tutor" in summary

    def test_empty_summary(self):
        reg = TemplateRegistry()
        assert "No templates" in reg.summary()


class TestBuildDefaultTemplateRegistry:
    def test_has_builtin_templates(self):
        reg = build_default_template_registry()
        names = reg.list_templates()
        assert len(names) >= 10
        assert "code_helper" in names
        assert "writing_assistant" in names
        assert "math_tutor" in names
        assert "health_advisor" in names
        assert "business_planner" in names
        assert "study_buddy" in names
        assert "creative_writer" in names
        assert "daily_planner" in names
        assert "language_tutor" in names
        assert "tech_support" in names

    def test_all_templates_have_required_fields(self):
        reg = build_default_template_registry()
        for name in reg.list_templates():
            t = reg.get(name)
            assert t.name, f"Template {name} has no name"
            assert t.title, f"Template {name} has no title"
            assert t.description, f"Template {name} has no description"
            assert t.icon, f"Template {name} has no icon"
            assert t.system_prompt_overlay, f"Template {name} has no overlay"
            assert t.greeting, f"Template {name} has no greeting"

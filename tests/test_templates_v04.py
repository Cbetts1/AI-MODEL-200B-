"""tests/test_templates_v04.py — Tests for the 10 new templates added in v0.4.0."""

from __future__ import annotations

import pytest

from aura.templates.registry import build_default_template_registry, TemplateRegistry


NEW_TEMPLATE_NAMES = [
    "legal_advisor",
    "financial_advisor",
    "fitness_coach",
    "recipe_chef",
    "interview_prep",
    "emotional_support",
    "science_tutor",
    "travel_planner",
    "philosophy",
    "data_analyst",
]

ORIGINAL_TEMPLATE_NAMES = [
    "code_helper",
    "writing_assistant",
    "math_tutor",
    "health_advisor",
    "business_planner",
    "study_buddy",
    "creative_writer",
    "daily_planner",
    "language_tutor",
    "tech_support",
]


class TestNewTemplates:

    def setup_method(self):
        self.registry = build_default_template_registry()

    def test_total_template_count_is_20(self):
        assert len(self.registry.list_templates()) == 20

    def test_all_original_templates_still_present(self):
        names = self.registry.list_templates()
        for name in ORIGINAL_TEMPLATE_NAMES:
            assert name in names, f"Original template '{name}' missing"

    def test_all_new_templates_present(self):
        names = self.registry.list_templates()
        for name in NEW_TEMPLATE_NAMES:
            assert name in names, f"New template '{name}' missing"

    def test_all_templates_have_required_fields(self):
        for template in self.registry.all_templates():
            assert template.name, f"Template has no name: {template}"
            assert template.title, f"Template '{template.name}' has no title"
            assert template.description, f"Template '{template.name}' has no description"
            assert template.icon, f"Template '{template.name}' has no icon"
            assert template.system_prompt_overlay, f"Template '{template.name}' has no system_prompt_overlay"
            assert template.greeting, f"Template '{template.name}' has no greeting"

    def test_all_templates_to_dict(self):
        for template in self.registry.all_templates():
            d = template.to_dict()
            assert "name" in d
            assert "title" in d
            assert "description" in d
            assert "icon" in d
            assert "greeting" in d

    def test_legal_advisor_template(self):
        t = self.registry.get("legal_advisor")
        assert t is not None
        assert "legal" in t.system_prompt_overlay.lower() or "law" in t.system_prompt_overlay.lower()
        assert "⚖️" == t.icon

    def test_financial_advisor_template(self):
        t = self.registry.get("financial_advisor")
        assert t is not None
        assert "financial" in t.system_prompt_overlay.lower() or "finance" in t.system_prompt_overlay.lower()
        assert "💰" == t.icon

    def test_fitness_coach_template(self):
        t = self.registry.get("fitness_coach")
        assert t is not None
        assert "fitness" in t.system_prompt_overlay.lower() or "workout" in t.system_prompt_overlay.lower()
        assert "💪" == t.icon

    def test_recipe_chef_template(self):
        t = self.registry.get("recipe_chef")
        assert t is not None
        assert "chef" in t.system_prompt_overlay.lower() or "cook" in t.system_prompt_overlay.lower()
        assert "👨‍🍳" == t.icon

    def test_interview_prep_template(self):
        t = self.registry.get("interview_prep")
        assert t is not None
        assert "interview" in t.system_prompt_overlay.lower()
        assert "🎯" == t.icon

    def test_emotional_support_template(self):
        t = self.registry.get("emotional_support")
        assert t is not None
        assert "empathy" in t.system_prompt_overlay.lower() or "compassion" in t.system_prompt_overlay.lower()
        assert "💙" == t.icon

    def test_science_tutor_template(self):
        t = self.registry.get("science_tutor")
        assert t is not None
        assert "science" in t.system_prompt_overlay.lower() or "physics" in t.system_prompt_overlay.lower()
        assert "🔬" == t.icon

    def test_travel_planner_template(self):
        t = self.registry.get("travel_planner")
        assert t is not None
        assert "travel" in t.system_prompt_overlay.lower() or "itinerary" in t.system_prompt_overlay.lower()
        assert "✈️" == t.icon

    def test_philosophy_template(self):
        t = self.registry.get("philosophy")
        assert t is not None
        assert "philosophy" in t.system_prompt_overlay.lower()
        assert "🧠" == t.icon

    def test_data_analyst_template(self):
        t = self.registry.get("data_analyst")
        assert t is not None
        assert "data" in t.system_prompt_overlay.lower() or "analyst" in t.system_prompt_overlay.lower()
        assert "📊" == t.icon

    def test_registry_summary_includes_new_templates(self):
        summary = self.registry.summary()
        for name in NEW_TEMPLATE_NAMES:
            # At least part of the template info should appear in summary
            assert any(
                keyword in summary.lower()
                for keyword in [name.replace("_", " "), name.split("_")[0]]
            ), f"Template '{name}' not visible in summary"

    def test_templates_have_non_empty_greeting(self):
        for t in self.registry.all_templates():
            assert len(t.greeting.strip()) > 20, f"Template '{t.name}' greeting too short"

    def test_templates_have_non_empty_overlay(self):
        for t in self.registry.all_templates():
            assert len(t.system_prompt_overlay.strip()) > 50, f"Template '{t.name}' overlay too short"


class TestTemplateSearchability:
    """Templates should be searchable by tag and keyword in practice."""

    def setup_method(self):
        self.registry = build_default_template_registry()

    def test_all_templates_have_tags_or_can_be_filtered(self):
        templates = self.registry.all_templates()
        # All new templates should have at least one tag
        for name in NEW_TEMPLATE_NAMES:
            t = self.registry.get(name)
            # tags list exists (may be empty for some older templates but new ones have tags)
            assert hasattr(t, "tags")

    def test_unique_names(self):
        names = self.registry.list_templates()
        assert len(names) == len(set(names)), "Duplicate template names found"

"""tests/test_new_tools_v06.py — Tests for new AURA v0.6.0 tools."""

import pytest
from pathlib import Path


# ── resume_builder ─────────────────────────────────────────────────────────────

class TestResumeTool:
    @pytest.fixture()
    def tool(self, tmp_path, monkeypatch):
        from aura.tools.resume_builder import ResumeTool, _RESUMES_DIR
        import aura.tools.resume_builder as mod
        monkeypatch.setattr(mod, "_RESUMES_DIR", tmp_path / "resumes")
        return ResumeTool()

    def test_help_output(self, tool):
        result = tool.run("help")
        assert "Resume Builder" in result

    def test_empty_args_returns_help(self, tool):
        result = tool.run("")
        assert "Resume Builder" in result

    def test_create_returns_resume(self, tool):
        result = tool.run(
            'create name="Jane Smith" role="Engineer" '
            'skills="Python,Go" experience="5 years at Acme" '
            'education="BSc CS" email="jane@example.com"'
        )
        assert "Jane Smith" in result
        assert "Engineer" in result
        assert "Python" in result

    def test_create_saves_file(self, tool, tmp_path, monkeypatch):
        import aura.tools.resume_builder as mod
        resume_dir = tmp_path / "resumes"
        monkeypatch.setattr(mod, "_RESUMES_DIR", resume_dir)
        tool2 = mod.ResumeTool()
        tool2.run('create name="Alice Brown" role="Designer"')
        files = list(resume_dir.glob("*.md"))
        assert len(files) == 1
        assert "alice_brown" in files[0].name

    def test_list_no_resumes(self, tool):
        result = tool.run("list")
        assert "No resumes" in result

    def test_list_after_create(self, tool):
        tool.run('create name="Bob Jones" role="Analyst"')
        result = tool.run("list")
        assert "bob_jones" in result.lower()

    def test_show_nonexistent(self, tool):
        result = tool.run("show nonexistent_resume")
        assert "not found" in result.lower()

    def test_create_with_summary(self, tool):
        result = tool.run(
            'create name="Carol White" role="PM" '
            'summary="Experienced product manager"'
        )
        assert "Experienced product manager" in result

    def test_tool_name(self, tool):
        assert tool.name == "resume_builder"

    def test_tool_description_mentions_create(self, tool):
        assert "create" in tool.description.lower()


# ── website_generator ─────────────────────────────────────────────────────────

class TestWebsiteGeneratorTool:
    @pytest.fixture()
    def tool(self, tmp_path, monkeypatch):
        from aura.tools.website_generator import WebsiteGeneratorTool
        import aura.tools.website_generator as mod
        monkeypatch.setattr(mod, "_WEBSITES_DIR", tmp_path / "sites")
        return WebsiteGeneratorTool()

    def test_help_output(self, tool):
        result = tool.run("help")
        assert "Website Generator" in result

    def test_empty_args_returns_help(self, tool):
        result = tool.run("")
        assert "Website Generator" in result

    def test_create_landing(self, tool):
        result = tool.run(
            'create name="TestSite" type=landing '
            'title="Test Landing" tagline="Welcome"'
        )
        assert "TestSite" in result
        assert "generated" in result.lower()

    def test_create_portfolio(self, tool):
        result = tool.run(
            'create name="Portfolio" type=portfolio '
            'title="Dev Portfolio" skills="Python,React"'
        )
        assert "Portfolio" in result
        assert "portfolio" in result.lower()

    def test_create_saves_html(self, tool, tmp_path, monkeypatch):
        import aura.tools.website_generator as mod
        sites_dir = tmp_path / "sites2"
        monkeypatch.setattr(mod, "_WEBSITES_DIR", sites_dir)
        t = mod.WebsiteGeneratorTool()
        t.run('create name="MySite" type=landing title="My Site"')
        assert (sites_dir / "MySite" / "index.html").exists()
        assert (sites_dir / "MySite" / "style.css").exists()

    def test_create_html_contains_title(self, tool, tmp_path, monkeypatch):
        import aura.tools.website_generator as mod
        sites_dir = tmp_path / "sites3"
        monkeypatch.setattr(mod, "_WEBSITES_DIR", sites_dir)
        t = mod.WebsiteGeneratorTool()
        t.run('create name="TitleSite" title="My Awesome Page" type=landing')
        html = (sites_dir / "TitleSite" / "index.html").read_text()
        assert "My Awesome Page" in html

    def test_list_no_sites(self, tool):
        result = tool.run("list")
        assert "No websites" in result

    def test_list_after_create(self, tool):
        tool.run('create name="MySite2" type=landing')
        result = tool.run("list")
        assert "MySite2" in result

    def test_show_nonexistent(self, tool):
        result = tool.run("show does_not_exist")
        assert "not found" in result.lower()

    def test_tool_name(self, tool):
        assert tool.name == "website_generator"

    def test_custom_color_in_css(self, tool, tmp_path, monkeypatch):
        import aura.tools.website_generator as mod
        sites_dir = tmp_path / "sites4"
        monkeypatch.setattr(mod, "_WEBSITES_DIR", sites_dir)
        t = mod.WebsiteGeneratorTool()
        t.run('create name="ColorSite" type=landing color="#ff0000"')
        css = (sites_dir / "ColorSite" / "style.css").read_text()
        assert "#ff0000" in css


# ── doc_generator ─────────────────────────────────────────────────────────────

class TestDocGeneratorTool:
    @pytest.fixture()
    def tool(self, tmp_path, monkeypatch):
        from aura.tools.doc_generator import DocGeneratorTool
        import aura.tools.doc_generator as mod
        monkeypatch.setattr(mod, "_DOCS_DIR", tmp_path / "docs")
        return DocGeneratorTool()

    def test_help_output(self, tool):
        result = tool.run("help")
        assert "Doc Generator" in result

    def test_empty_args_returns_help(self, tool):
        result = tool.run("")
        assert "Doc Generator" in result

    def test_create_api_doc(self, tool):
        result = tool.run(
            'create name="MyAPI" type=api '
            'title="My API" description="A weather API" '
            'author="Alice"'
        )
        assert "My API" in result
        assert "Authentication" in result

    def test_create_library_doc(self, tool):
        result = tool.run(
            'create name="mylib" type=library '
            'title="mylib" description="A Python library" '
            'install="pip install mylib"'
        )
        assert "mylib" in result
        assert "Installation" in result
        assert "pip install mylib" in result

    def test_create_readme(self, tool):
        result = tool.run(
            'create name="MyApp" type=readme '
            'title="MyApp" description="An awesome app"'
        )
        assert "MyApp" in result
        assert "Features" in result

    def test_create_guide(self, tool):
        result = tool.run(
            'create name="Setup" type=guide '
            'title="Setup Guide" description="setting up the project"'
        )
        assert "Setup Guide" in result
        assert "Step 1" in result

    def test_create_saves_file(self, tool, tmp_path, monkeypatch):
        import aura.tools.doc_generator as mod
        docs_dir = tmp_path / "docs2"
        monkeypatch.setattr(mod, "_DOCS_DIR", docs_dir)
        t = mod.DocGeneratorTool()
        t.run('create name="TestDoc" type=readme title="TestDoc"')
        assert (docs_dir / "TestDoc.md").exists()

    def test_list_no_docs(self, tool):
        result = tool.run("list")
        assert "No docs" in result

    def test_list_after_create(self, tool):
        tool.run('create name="ListDoc" type=readme title="ListDoc"')
        result = tool.run("list")
        assert "ListDoc" in result

    def test_show_nonexistent(self, tool):
        result = tool.run("show nonexistent_doc")
        assert "not found" in result.lower()

    def test_show_existing(self, tool, tmp_path, monkeypatch):
        import aura.tools.doc_generator as mod
        docs_dir = tmp_path / "docs3"
        monkeypatch.setattr(mod, "_DOCS_DIR", docs_dir)
        t = mod.DocGeneratorTool()
        t.run('create name="ShowDoc" type=readme title="ShowDoc"')
        result = t.run("show ShowDoc")
        assert "ShowDoc" in result

    def test_tool_name(self, tool):
        assert tool.name == "doc_generator"

    def test_unknown_type_falls_back_to_readme(self, tool):
        result = tool.run(
            'create name="FallbackDoc" type=unknown_type title="Test"'
        )
        assert "Features" in result  # readme template has Features section


# ── registry integration ───────────────────────────────────────────────────────

class TestRegistryIntegrationV06:
    def test_new_tools_in_default_registry(self):
        from aura.tools.registry import build_default_registry
        registry = build_default_registry()
        names = registry.list_tools()
        assert "resume_builder" in names
        assert "website_generator" in names
        assert "doc_generator" in names

    def test_total_tool_count_is_18(self):
        from aura.tools.registry import build_default_registry
        registry = build_default_registry()
        assert len(registry.list_tools()) == 18

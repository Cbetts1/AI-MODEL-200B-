"""tests/test_workflows.py — Unit tests for AURA workflows."""

import pytest
from pathlib import Path

from aura.workflows.app_scaffold import AppScaffoldWorkflow


class TestAppScaffoldWorkflow:
    def test_scaffold_creates_files(self, tmp_path):
        wf = AppScaffoldWorkflow()
        output = str(tmp_path / "MyApp")
        result = wf.run(f"MyApp com.example.myapp {output}")

        assert "Done" in result or "succeeded" in result.lower() or "Scaffolding" in result

        root = Path(output)
        assert (root / "settings.gradle").exists()
        assert (root / "build.gradle").exists()
        assert (root / "app" / "build.gradle").exists()
        assert (root / "app" / "src" / "main" / "AndroidManifest.xml").exists()
        # Layout file must exist so the setContentView reference compiles
        layout_file = root / "app/src/main/res/layout/activity_main.xml"
        assert layout_file.exists()
        java_file = root / "app/src/main/java/com/example/myapp/MainActivity.java"
        assert java_file.exists()
        assert "com.example.myapp" in java_file.read_text()

    def test_scaffold_missing_args(self):
        wf = AppScaffoldWorkflow()
        result = wf.run("MyApp")
        assert "Usage" in result

    def test_gradlew_is_executable(self, tmp_path):
        wf = AppScaffoldWorkflow()
        output = str(tmp_path / "ExecTest")
        wf.run(f"ExecTest com.example.exec {output}")
        gradlew = tmp_path / "ExecTest" / "gradlew"
        assert gradlew.exists()
        assert gradlew.stat().st_mode & 0o111  # at least one executable bit set

    def test_manifest_contains_package(self, tmp_path):
        wf = AppScaffoldWorkflow()
        output = str(tmp_path / "PkgTest")
        wf.run(f"PkgTest org.test.pkg {output}")
        manifest = Path(output) / "app/src/main/AndroidManifest.xml"
        content = manifest.read_text()
        assert "org.test.pkg" in content

    def test_workflow_name(self):
        assert AppScaffoldWorkflow.name == "app_scaffold"

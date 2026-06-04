"""Tests for project and quality checks."""

from pathlib import Path

from drifter.config import Config
from drifter.checks.security import CredentialLeakCheck
from drifter.checks.code_quality import DeadCodeCheck, TestCoverageCheck
from drifter.checks.sync import ReadmeCompletenessCheck, PreFlightSyncCheck


class TestReadmeCompletenessCheck:
    def test_missing_mentions(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        readme = tmp_path / "README.md"
        readme.write_text("# Project\n\nJust a project.\n")
        check = ReadmeCompletenessCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) > 0
        assert any("dangerous_patterns.toml" in i.detail for i in issues)

    def test_complete_readme(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        readme = tmp_path / "README.md"
        readme.write_text(
            "# Project\n"
            "AGENTS.md, dangerous_patterns.toml, session-protocol.md, project-conductor.md\n"
            "drifter check, drifter preflight, drifter conductor, "
            "drifter validate, drifter audit, drifter init\n"
        )
        check = ReadmeCompletenessCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_missing_readme(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        check = ReadmeCompletenessCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "does not exist" in issues[0].detail


class TestPreFlightSyncCheck:
    def test_step_mismatch(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        preflight = tmp_path / "src" / "drifter" / "pre_flight.py"
        preflight.parent.mkdir(parents=True)
        preflight.write_text(
            "# Step 1:\n# Step 2:\n# Step 3:\n# Step 4:\n# Step 5:\n# Step 6:\n# Step 7:\n"
        )
        protocol = tmp_path / "docs" / "session-protocol.md"
        protocol.parent.mkdir(parents=True)
        protocol.write_text(
            "## The 7-Step Pre-Flight\n\n"
            "1. READ\n2. READ\n3. READ\n4. RUN\n5. PICK\n6. GREP\n"
        )
        check = PreFlightSyncCheck()
        issues = check.run(tmp_path, config)
        assert any(
            "pre_flight.py has 7 steps but protocol lists 6" in i.detail for i in issues
        )

    def test_synced_steps_pass(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        preflight = tmp_path / "src" / "drifter" / "pre_flight.py"
        preflight.parent.mkdir(parents=True)
        preflight.write_text(
            "# Step 1:\n# Step 2:\n# Step 3:\n# Step 4:\n# Step 5:\n# Step 6:\n# Step 7:\n"
            "dangerous_patterns.toml\n"
        )
        protocol = tmp_path / "docs" / "session-protocol.md"
        protocol.parent.mkdir(parents=True)
        protocol.write_text(
            "## The 7-Step Pre-Flight\n\n"
            "1. READ\n2. READ\n3. READ\n4. RUN\n5. PICK\n6. GREP\n7. READ\n"
            "dangerous_patterns.toml\n"
        )
        check = PreFlightSyncCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_methodology_drift(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        preflight = tmp_path / "src" / "drifter" / "pre_flight.py"
        preflight.parent.mkdir(parents=True)
        preflight.write_text(
            "# Step 1:\n# Step 2:\n# Step 3:\n# Step 4:\n# Step 5:\n# Step 6:\n# Step 7:\n"
        )
        methodology = tmp_path / "docs" / "methodology.md"
        methodology.parent.mkdir(parents=True)
        methodology.write_text("The 6-step pre-flight is a gate.\n")
        check = PreFlightSyncCheck()
        issues = check.run(tmp_path, config)
        assert any("methodology.md" in i.file and "6-step" in i.detail for i in issues)

    def test_readme_drift(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        preflight = tmp_path / "src" / "drifter" / "pre_flight.py"
        preflight.parent.mkdir(parents=True)
        preflight.write_text(
            "# Step 1:\n# Step 2:\n# Step 3:\n# Step 4:\n# Step 5:\n# Step 6:\n# Step 7:\n"
        )
        readme = tmp_path / "README.md"
        readme.write_text("We use a 5-step pre-flight protocol.\n")
        check = PreFlightSyncCheck()
        issues = check.run(tmp_path, config)
        assert any("README.md" in i.file and "5-step" in i.detail for i in issues)


class TestCredentialLeakCheck:
    def test_detects_api_key(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "main.py"
        src.parent.mkdir(parents=True)
        src.write_text('api_key = "sk-abcdefghijklmnopqrstuvwxyz123456"')
        check = CredentialLeakCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "OpenAI API key" in issues[0].detail

    def test_ignores_example(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "main.py"
        src.parent.mkdir(parents=True)
        src.write_text('api_key = "sk-your_example_key_here"')
        check = CredentialLeakCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_ignores_comment(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "main.py"
        src.parent.mkdir(parents=True)
        src.write_text('# api_key = "sk-abcdefghijklmnopqrstuvwxyz123456"')
        check = CredentialLeakCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestDeadCodeCheck:
    def test_unimported_module(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        (tmp_path / "src" / "used.py").parent.mkdir(parents=True)
        (tmp_path / "src" / "used.py").write_text("def foo(): pass\n")
        (tmp_path / "src" / "unused.py").write_text("def bar(): pass\n")
        (tmp_path / "src" / "main.py").write_text("from used import foo\n")
        check = DeadCodeCheck()
        issues = check.run(tmp_path, config)
        assert any("unused" in i.detail for i in issues)

    def test_imported_module_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        (tmp_path / "src" / "helper.py").parent.mkdir(parents=True)
        (tmp_path / "src" / "helper.py").write_text("def bar(): pass\n")
        (tmp_path / "src" / "app.py").write_text("from helper import bar\n")
        (tmp_path / "tests" / "test_app.py").parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "tests" / "test_app.py").write_text("pass\n")
        check = DeadCodeCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestTestCoverageCheck:
    def test_missing_test(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        (tmp_path / "src" / "drifter" / "foo.py").parent.mkdir(parents=True)
        (tmp_path / "src" / "drifter" / "foo.py").write_text("pass\n")
        (tmp_path / "tests").mkdir()
        check = TestCoverageCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "test_foo.py" in issues[0].detail

    def test_has_test_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        (tmp_path / "src" / "drifter" / "foo.py").parent.mkdir(parents=True)
        (tmp_path / "src" / "drifter" / "foo.py").write_text("pass\n")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_foo.py").write_text("pass\n")
        check = TestCoverageCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

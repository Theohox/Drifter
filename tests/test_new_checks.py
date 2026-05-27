"""Tests for new drift guard checks (Phase 2 — self-reflection checks)."""

from pathlib import Path

from drifter.config import Config
from drifter.drift_guard import (
    ArchitectureDocSyncCheck,
    CliOutputCheck,
    ConductorContentCheck,
    CredentialLeakCheck,
    DeadCodeCheck,
    GitignoreCheck,
    PreFlightSyncCheck,
    ReadmeCompletenessCheck,
    TestCoverageCheck,
    TimestampStalenessCheck,
)


class TestTimestampStalenessCheck:
    def test_detects_stale_timestamp(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        doc = tmp_path / "docs" / "readme.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("---\nupdated: '2020-01-01T00:00:00Z'\n---\n\n# Readme\n")
        check = TimestampStalenessCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert issues[0].check == "timestamp_staleness"

    def test_fresh_timestamp_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        doc = tmp_path / "docs" / "readme.md"
        doc.parent.mkdir(parents=True)
        doc.write_text(f"---\nupdated: '{now}'\n---\n\n# Readme\n")
        check = TimestampStalenessCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestConductorContentCheck:
    def test_empty_evidence(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        conductor = tmp_path / "docs" / "project-conductor.md"
        conductor.parent.mkdir(parents=True)
        conductor.write_text(
            "---\ntype: backlog\n---\n"
            "## Active Task\n| Field | Value |\n"
            "| **Evidence** | — |\n"
            "## Drift Score History\n"
            "| Timestamp | Score | Tests | Notes |\n"
            "|-----------|-------|-------|-------|\n"
            "| — | — | — | — |\n"
        )
        check = ConductorContentCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 2
        assert any("evidence is empty" in i.detail for i in issues)
        assert any("History is empty" in i.detail for i in issues)

    def test_valid_conductor_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        conductor = tmp_path / "docs" / "project-conductor.md"
        conductor.parent.mkdir(parents=True)
        conductor.write_text(
            "---\ntype: backlog\n---\n"
            "## Active Task\n| Field | Value |\n| **Evidence** | tests pass |\n"
            "## Drift Score History\n"
            "| Timestamp | Score | Tests | Notes |\n"
            "|-----------|-------|-------|-------|\n"
            "| 2026-01-01 | 100/100 | 10 | good |\n"
        )
        check = ConductorContentCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestArchitectureDocSyncCheck:
    def test_mismatch(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        arch = tmp_path / "docs" / "architecture.md"
        arch.parent.mkdir(parents=True)
        arch.write_text(
            "# Architecture\n• StaleReferenceCheck\n• HardcodedPathCheck\n"
        )
        guard = tmp_path / "src" / "drifter" / "drift_guard.py"
        guard.parent.mkdir(parents=True)
        guard.write_text(
            "class StaleReferenceCheck:\n"
            "class HardcodedPathCheck:\n"
            "class DigestStalenessCheck:\n"
        )
        cli = tmp_path / "src" / "drifter" / "cli.py"
        cli.parent.mkdir(parents=True, exist_ok=True)
        cli.write_text('subparsers.add_parser("check")')
        check = ArchitectureDocSyncCheck()
        issues = check.run(tmp_path, config)
        assert any("lists 2 checks but drift_guard.py has 3" in i.detail for i in issues)

    def test_no_architecture_doc(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        check = ArchitectureDocSyncCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_template_count_drift(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        arch = tmp_path / "docs" / "architecture.md"
        arch.parent.mkdir(parents=True)
        arch.write_text("# Architecture\n")
        guard = tmp_path / "src" / "drifter" / "drift_guard.py"
        guard.parent.mkdir(parents=True)
        guard.write_text(
            "class StaleReferenceCheck:\n"
            "class HardcodedPathCheck:\n"
            "class DigestStalenessCheck:\n"
        )
        toml_tmpl = tmp_path / "templates" / "drifter.toml.tmpl"
        toml_tmpl.parent.mkdir(parents=True)
        toml_tmpl.write_text("# Built-in checks (5 total)\n")
        check = ArchitectureDocSyncCheck()
        issues = check.run(tmp_path, config)
        assert any("templates/drifter.toml.tmpl" in i.file for i in issues)
        assert any("claims 5 built-in checks" in i.detail for i in issues)


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
        assert any("pre_flight.py has 7 steps but protocol lists 6" in i.detail for i in issues)

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


class TestCliOutputCheck:
    def test_missing_mention(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        cli = tmp_path / "src" / "drifter" / "cli.py"
        cli.parent.mkdir(parents=True)
        cli.write_text(
            'def cmd_init(args):\n'
            '    print("AGENTS.md")\n'
            '    print("session-protocol.md")\n'
            '    print("project-conductor.md")\n'
        )
        check = CliOutputCheck()
        issues = check.run(tmp_path, config)
        assert any("dangerous_patterns.toml" in i.detail for i in issues)

    def test_all_mentions_present(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        cli = tmp_path / "src" / "drifter" / "cli.py"
        cli.parent.mkdir(parents=True)
        cli.write_text(
            'def cmd_init(args):\n'
            '    print("AGENTS.md")\n'
            '    print("dangerous_patterns.toml")\n'
            '    print("session-protocol.md")\n'
            '    print("project-conductor.md")\n'
        )
        check = CliOutputCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestGitignoreCheck:
    def test_missing_gitignore(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        check = GitignoreCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "does not exist" in issues[0].detail

    def test_sensitive_file_not_ignored(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        (tmp_path / ".gitignore").write_text("*.pyc\n")
        (tmp_path / ".env").write_text("SECRET=123\n")
        (tmp_path / "dangerous_patterns.toml").write_text(
            '[filesystem]\nsensitive_patterns = [".env"]\n'
        )
        check = GitignoreCheck()
        issues = check.run(tmp_path, config)
        assert any(".env" in i.detail for i in issues)

    def test_sensitive_file_ignored(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        (tmp_path / ".gitignore").write_text(".env\n")
        (tmp_path / ".env").write_text("SECRET=123\n")
        check = GitignoreCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

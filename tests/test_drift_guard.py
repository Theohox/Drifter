"""Tests for drift guard engine."""

from pathlib import Path

from drifter.config import Config
from drifter.drift_guard import (
    ArchiveIntegrityCheck,
    AuditCoverageCheck,
    ConductorHealthCheck,
    CrossDocConsistencyCheck,
    DigestStalenessCheck,
    HardcodedPathCheck,
    ReporterCompletenessCheck,
    StaleReferenceCheck,
    TemplateCountSyncCheck,
    TomllibCompatibilityCheck,
    run_checks,
)


class TestStaleReferenceCheck:
    def test_detects_stale_ref(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        doc = tmp_path / "docs" / "readme.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("See `src/nonexistent.py` for details.")

        check = StaleReferenceCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert issues[0].check == "stale_reference"
        assert "nonexistent.py" in issues[0].detail

    def test_ignores_existing_file(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        doc = tmp_path / "docs" / "readme.md"
        doc.parent.mkdir(parents=True)
        existing = tmp_path / "src" / "exists.py"
        existing.parent.mkdir(parents=True)
        existing.write_text("# exists")
        doc.write_text("See `src/exists.py` for details.")

        check = StaleReferenceCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestHardcodedPathCheck:
    def test_detects_hardcoded_path(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "main.py"
        src.parent.mkdir(parents=True)
        # Use a path that does NOT exist so the check flags it
        src.write_text('path = "docs/bogus_file.md"')

        check = HardcodedPathCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert issues[0].check == "hardcoded_path"


class TestConductorHealthCheck:
    def test_missing_conductor(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        check = ConductorHealthCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "not exist" in issues[0].detail

    def test_healthy_conductor(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        conductor = tmp_path / "docs" / "project-conductor.md"
        conductor.parent.mkdir(parents=True)
        conductor.write_text("""
## Current Phase
**Phase 1** 🟢 ACTIVE

## Active Task
| ID | Name |
|----|------|
| 1 | Do thing |
""")
        check = ConductorHealthCheck()
        issues = check.run(tmp_path, config)
        # Should pass — one active task, active phase
        assert len(issues) == 0


class TestArchiveIntegrityCheck:
    def test_valid_archive_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        archive = tmp_path / "docs" / "archive" / "FEAT-001-foundation.md"
        archive.parent.mkdir(parents=True)
        archive.write_text(
            "---\n"
            "type: archive\n"
            "status: archived\n"
            "task_id: FEAT-001\n"
            "---\n\n"
            "# FEAT-001\n"
        )
        check = ArchiveIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_missing_frontmatter(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        archive = tmp_path / "docs" / "archive" / "FEAT-001-foundation.md"
        archive.parent.mkdir(parents=True)
        archive.write_text("# No frontmatter\n")
        check = ArchiveIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "Missing YAML frontmatter" in issues[0].detail

    def test_wrong_type(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        archive = tmp_path / "docs" / "archive" / "FEAT-001-foundation.md"
        archive.parent.mkdir(parents=True)
        archive.write_text(
            "---\n"
            "type: backlog\n"
            "task_id: FEAT-001\n"
            "---\n\n"
            "# FEAT-001\n"
        )
        check = ArchiveIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "Invalid type 'backlog'" in issues[0].detail

    def test_filename_mismatch(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        archive = tmp_path / "docs" / "archive" / "FEAT-001-foundation.md"
        archive.parent.mkdir(parents=True)
        archive.write_text(
            "---\n"
            "type: archive\n"
            "task_id: WRONG-ID\n"
            "---\n\n"
            "# FEAT-001\n"
        )
        check = ArchiveIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "does not match task_id" in issues[0].detail

    def test_readme_skipped(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        archive = tmp_path / "docs" / "archive" / "README.md"
        archive.parent.mkdir(parents=True)
        archive.write_text("# Archive README\n")
        check = ArchiveIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestTomllibCompatibilityCheck:
    def test_detects_bare_tomllib(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "drifter" / "foo.py"
        src.parent.mkdir(parents=True)
        src.write_text("import tomllib\n")
        check = TomllibCompatibilityCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "bare 'import tomllib'" in issues[0].detail

    def test_allows_guarded_tomllib(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "drifter" / "foo.py"
        src.parent.mkdir(parents=True)
        src.write_text(
            "import sys\n"
            "if sys.version_info >= (3, 11):\n"
            "    import tomllib\n"
            "else:\n"
            "    import tomli as tomllib\n"
        )
        check = TomllibCompatibilityCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestAuditCoverageCheck:
    def test_missing_warn_action(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        cli = tmp_path / "src" / "drifter" / "cli.py"
        cli.parent.mkdir(parents=True)
        cli.write_text(
            'def cmd_audit(args):\n'
            '    if classification.action in ("block", "approval_required"):\n'
            '        violations.append((line, classification))\n'
        )
        guard = tmp_path / "src" / "drifter" / "shell_guard.py"
        guard.parent.mkdir(parents=True, exist_ok=True)
        guard.write_text(
            'action="block"\n'
            'action="approval_required"\n'
            'action="warn"\n'
        )
        check = AuditCoverageCheck()
        issues = check.run(tmp_path, config)
        assert any("'warn'" in i.detail for i in issues)

    def test_all_actions_covered(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        cli = tmp_path / "src" / "drifter" / "cli.py"
        cli.parent.mkdir(parents=True)
        cli.write_text(
            'def cmd_audit(args):\n'
            '    if classification.action in ("block", "approval_required", "warn"):\n'
            '        violations.append((line, classification))\n'
        )
        guard = tmp_path / "src" / "drifter" / "shell_guard.py"
        guard.parent.mkdir(parents=True, exist_ok=True)
        guard.write_text(
            'action="block"\n'
            'action="approval_required"\n'
            'action="warn"\n'
        )
        check = AuditCoverageCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestReporterCompletenessCheck:
    def test_missing_info_severity(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        cli = tmp_path / "src" / "drifter" / "cli.py"
        cli.parent.mkdir(parents=True)
        cli.write_text(
            'def _format_issues_console(issues, score=None):\n'
            '    for issue in issues:\n'
            '        if issue.severity == "error":\n'
            '            print(f"ERROR: {issue}")\n'
            '        elif issue.severity == "warn":\n'
            '            print(f"WARN: {issue}")\n'
        )
        check = ReporterCompletenessCheck()
        issues = check.run(tmp_path, config)
        assert any("'info'" in i.detail for i in issues)

    def test_all_severities_present(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        cli = tmp_path / "src" / "drifter" / "cli.py"
        cli.parent.mkdir(parents=True)
        cli.write_text(
            'def _format_issues_console(issues, score=None):\n'
            '    errors = [i for i in issues if i.severity == "error"]\n'
            '    warns = [i for i in issues if i.severity == "warn"]\n'
            '    infos = [i for i in issues if i.severity == "info"]\n'
        )
        check = ReporterCompletenessCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestTemplateCountSyncCheck:
    def test_check_count_mismatch(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        tmpl = tmp_path / "templates" / "drifter.toml.tmpl"
        tmpl.parent.mkdir(parents=True)
        tmpl.write_text("# Built-in checks (5 total)\n")
        guard = tmp_path / "src" / "drifter" / "drift_guard.py"
        guard.parent.mkdir(parents=True)
        guard.write_text(
            "class StaleReferenceCheck:\n"
            "class HardcodedPathCheck:\n"
            "class DigestStalenessCheck:\n"
        )
        check = TemplateCountSyncCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "claims 5 built-in checks" in issues[0].detail

    def test_step_count_mismatch(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        tmpl = tmp_path / "templates" / "foo.md.tmpl"
        tmpl.parent.mkdir(parents=True)
        tmpl.write_text("The 6-step pre-flight protocol.\n")
        preflight = tmp_path / "src" / "drifter" / "pre_flight.py"
        preflight.parent.mkdir(parents=True)
        preflight.write_text(
            "# Step 1:\n# Step 2:\n# Step 3:\n# Step 4:\n# Step 5:\n# Step 6:\n# Step 7:\n"
        )
        check = TemplateCountSyncCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "claims 6-step pre-flight" in issues[0].detail

    def test_synced_counts_pass(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        tmpl = tmp_path / "templates" / "drifter.toml.tmpl"
        tmpl.parent.mkdir(parents=True)
        tmpl.write_text("# Built-in checks (3 total)\n")
        guard = tmp_path / "src" / "drifter" / "drift_guard.py"
        guard.parent.mkdir(parents=True)
        guard.write_text(
            "class StaleReferenceCheck:\n"
            "class HardcodedPathCheck:\n"
            "class DigestStalenessCheck:\n"
        )
        check = TemplateCountSyncCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestRunChecks:
    def test_empty_project(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        # Create minimal required files to avoid drift guard errors
        docs = tmp_path / "docs"
        docs.mkdir()
        conductor = docs / "project-conductor.md"
        conductor.write_text("""
---
title: Conductor
type: backlog
---
## Current Phase
**Phase 1** 🟢 ACTIVE
## Active Task
| ID | Name |
| 1 | Task |
""")
        # Create dangerous_patterns.toml and AGENTS.md to pass DangerousPatternsCheck
        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text("[git]\nalways_block = [\"git commit\"]\n[shell]\nblocked = []\n")
        agents = tmp_path / "AGENTS.md"
        agents.write_text("# AGENTS.md\n\nRead dangerous_patterns.toml before running commands.\n")
        # Create README.md and .gitignore to pass ReadmeCompletenessCheck and GitignoreCheck
        readme = tmp_path / "README.md"
        readme.write_text(
            "# Project\n"
            "AGENTS.md dangerous_patterns.toml session-protocol.md project-conductor.md\n"
            "drifter check drifter preflight drifter conductor "
            "drifter validate drifter audit drifter init\n"
        )
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".env\n")
        report = run_checks(root=tmp_path, config=config)
        assert report.score == 100
        assert report.total == 0

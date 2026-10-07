"""Tests for sync verification checks (checks/sync.py)."""

from pathlib import Path

from drifter.checks.sync import (
    ArchitectureDocSyncCheck,
    AuditCoverageCheck,
    CliOutputCheck,
    DocCoverageCheck,
    PreFlightSyncCheck,
    ReadmeCompletenessCheck,
    ReporterCompletenessCheck,
)
from drifter.config import Config


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class TestArchitectureDocSyncCheckCounts:
    def test_matching_check_count_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(
            tmp_path / "docs" / "architecture.md",
            "# Architecture\n• StaleReferenceCheck\n• GitSafetyCheck\n",
        )
        _write(
            tmp_path / "src" / "drifter" / "checks" / "docs.py",
            "class StaleReferenceCheck:\nclass GitSafetyCheck:\n",
        )
        issues = ArchitectureDocSyncCheck().run(tmp_path, config)
        assert not any("checks" in i.detail for i in issues)

    def test_command_count_mismatch(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(
            tmp_path / "docs" / "architecture.md",
            "# Architecture\n`drifter check`\n`drifter init`\n",
        )
        _write(
            tmp_path / "src" / "drifter" / "cli.py",
            'subparsers.add_parser("check")\n',
        )
        issues = ArchitectureDocSyncCheck().run(tmp_path, config)
        assert any("lists 2 CLI commands but cli.py has 1" in i.detail for i in issues)

    def test_template_count_matches(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(tmp_path / "docs" / "architecture.md", "# Architecture\n")
        _write(
            tmp_path / "src" / "drifter" / "checks" / "docs.py",
            "class StaleReferenceCheck:\nclass GitSafetyCheck:\n",
        )
        _write(
            tmp_path / "src" / "drifter" / "templates" / "drifter.toml.tmpl",
            "# Built-in checks (2 total)\n",
        )
        issues = ArchitectureDocSyncCheck().run(tmp_path, config)
        assert len(issues) == 0


class TestPreFlightSyncCheckDocstring:
    def test_docstring_step_claim_mismatch(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(
            tmp_path / "src" / "drifter" / "pre_flight.py",
            '"""Run the 5-step pre-flight."""\n'
            "# Step 1:\n# Step 2:\n# Step 3:\n"
            "dangerous_patterns.toml\n",
        )
        issues = PreFlightSyncCheck().run(tmp_path, config)
        assert any(
            "claims 5-step pre-flight but file has 3 steps" in i.detail for i in issues
        )

    def test_missing_dangerous_patterns_reference(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(tmp_path / "src" / "drifter" / "pre_flight.py", "# Step 1:\n")
        issues = PreFlightSyncCheck().run(tmp_path, config)
        assert any(
            "does not verify dangerous_patterns.toml exists" in i.detail for i in issues
        )


class TestReadmeCompletenessCheckLeniency:
    def test_stale_readme_skipped(self, tmp_path: Path) -> None:
        """A README older than the drifter install is not enforced."""
        import os

        config = Config.load(root=tmp_path)
        readme = tmp_path / "README.md"
        readme.write_text("# Project\n")
        drifter_toml = tmp_path / "drifter.toml"
        drifter_toml.write_text("[drifter]\n")
        old = 1_000_000_000
        os.utime(readme, (old, old))
        issues = ReadmeCompletenessCheck().run(tmp_path, config)
        assert len(issues) == 0


class TestCliOutputCheckEdges:
    def test_no_init_module_no_issues(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        issues = CliOutputCheck().run(tmp_path, config)
        assert len(issues) == 0

    def test_no_cmd_init_function_no_issues(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(
            tmp_path / "src" / "drifter" / "_cli_init.py", "def other():\n    pass\n"
        )
        issues = CliOutputCheck().run(tmp_path, config)
        assert len(issues) == 0


class TestAuditCoverageCheck:
    def test_missing_warn_action(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(
            tmp_path / "src" / "drifter" / "_cli_admin.py",
            "def cmd_audit(args):\n"
            '    if classification.action in ("block", "approval_required"):\n'
            "        violations.append((line, classification))\n",
        )
        _write(
            tmp_path / "src" / "drifter" / "shell_guard.py",
            'action="block"\naction="approval_required"\naction="warn"\n',
        )
        issues = AuditCoverageCheck().run(tmp_path, config)
        assert any("'warn'" in i.detail for i in issues)

    def test_all_actions_covered(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(
            tmp_path / "src" / "drifter" / "_cli_admin.py",
            "def cmd_audit(args):\n"
            '    if classification.action in ("block", "approval_required", "warn"):\n'
            "        violations.append((line, classification))\n",
        )
        _write(
            tmp_path / "src" / "drifter" / "shell_guard.py",
            'action="block"\naction="approval_required"\naction="warn"\n',
        )
        issues = AuditCoverageCheck().run(tmp_path, config)
        assert len(issues) == 0

    def test_no_cmd_audit_no_issues(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(
            tmp_path / "src" / "drifter" / "_cli_admin.py", "def other():\n    pass\n"
        )
        _write(
            tmp_path / "src" / "drifter" / "shell_guard.py",
            'action="block"\n',
        )
        issues = AuditCoverageCheck().run(tmp_path, config)
        assert len(issues) == 0

    def test_allow_action_not_required(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(
            tmp_path / "src" / "drifter" / "_cli_admin.py",
            "def cmd_audit(args):\n    pass\n",
        )
        _write(
            tmp_path / "src" / "drifter" / "shell_guard.py",
            'action="allow"\n',
        )
        issues = AuditCoverageCheck().run(tmp_path, config)
        assert len(issues) == 0


class TestReporterCompletenessCheck:
    def test_missing_info_severity(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(
            tmp_path / "src" / "drifter" / "reporters" / "console.py",
            "class ConsoleReporter:\n"
            "    def report(self, issues, meta=None):\n"
            "        lines = []\n"
            '        errors = [i for i in issues if i.severity == "error"]\n'
            '        warns = [i for i in issues if i.severity == "warn"]\n'
            "        return str(lines)\n",
        )
        issues = ReporterCompletenessCheck().run(tmp_path, config)
        assert any("'info'" in i.detail for i in issues)

    def test_all_severities_present(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(
            tmp_path / "src" / "drifter" / "reporters" / "console.py",
            "class ConsoleReporter:\n"
            "    def report(self, issues, meta=None):\n"
            '        errors = [i for i in issues if i.severity == "error"]\n'
            '        warns = [i for i in issues if i.severity == "warn"]\n'
            '        infos = [i for i in issues if i.severity == "info"]\n'
            "        return str(errors + warns + infos)\n",
        )
        issues = ReporterCompletenessCheck().run(tmp_path, config)
        assert len(issues) == 0

    def test_no_report_method_no_issues(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(
            tmp_path / "src" / "drifter" / "reporters" / "console.py",
            "class ConsoleReporter:\n    pass\n",
        )
        issues = ReporterCompletenessCheck().run(tmp_path, config)
        assert len(issues) == 0


class TestDocCoverageCheck:
    def test_agents_md_missing_module(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(tmp_path / "AGENTS.md", "# Agent contract\n")
        _write(tmp_path / "src" / "drifter" / "shell_guard.py", "# guard\n")
        issues = DocCoverageCheck().run(tmp_path, config)
        assert any(
            "does not mention module 'shell_guard.py'" in i.detail for i in issues
        )

    def test_readme_missing_feature(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(tmp_path / "README.md", "# Project\nNothing here.\n")
        issues = DocCoverageCheck().run(tmp_path, config)
        assert any("does not mention feature 'enforcement'" in i.detail for i in issues)

    def test_template_divergence(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(tmp_path / "dangerous_patterns.toml", "[agent]\n")
        _write(
            tmp_path / "src" / "drifter" / "templates" / "dangerous_patterns.toml.tmpl",
            "[agent]\n# different\n",
        )
        issues = DocCoverageCheck().run(tmp_path, config)
        assert any("diverges from template" in i.detail for i in issues)

    def test_in_sync_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        _write(tmp_path / "AGENTS.md", "# Agent contract\nshell_guard.py\n")
        _write(tmp_path / "src" / "drifter" / "shell_guard.py", "# guard\n")
        _write(
            tmp_path / "README.md",
            "enforcement dangerous_patterns session audit pre-flight conductor\n",
        )
        body = "[agent]\n"
        _write(tmp_path / "dangerous_patterns.toml", body)
        _write(
            tmp_path / "src" / "drifter" / "templates" / "dangerous_patterns.toml.tmpl",
            body,
        )
        issues = DocCoverageCheck().run(tmp_path, config)
        assert len(issues) == 0

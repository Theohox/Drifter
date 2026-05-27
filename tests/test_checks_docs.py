"""Tests for documentation checks."""

from pathlib import Path

from drifter.config import Config
from drifter.checks.docs import TimestampStalenessCheck
from drifter.checks.project import ConductorContentCheck
from drifter.checks.sync import ArchitectureDocSyncCheck


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
        assert any("lists 2 checks but checks package has 3" in i.detail for i in issues)

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

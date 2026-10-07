"""Tests for docs, code-quality, and project checks.

Covers StaleReferenceCheck and ArchiveIntegrityCheck (checks/docs.py),
HardcodedPathCheck (checks/code_quality.py), and ConductorHealthCheck
(checks/project.py).
"""

from pathlib import Path

from drifter.checks.code_quality import HardcodedPathCheck
from drifter.checks.docs import (
    ArchiveIntegrityCheck,
    StaleReferenceCheck,
)
from drifter.checks.project import ConductorHealthCheck
from drifter.config import Config


class TestStaleReferenceCheck:
    def test_detects_stale_ref(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        doc = tmp_path / "docs" / "readme.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("See `src/definitely_gone.py` for details.")

        check = StaleReferenceCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert issues[0].check == "stale_reference"
        assert "definitely_gone.py" in issues[0].detail

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
        assert len(issues) == 0

    def test_awaiting_state_is_not_a_warning(self, tmp_path: Path) -> None:
        """The Stop Rule makes 'no ACTIVE phase, waiting on the human' a valid
        state — declared with an AWAITING marker, it must not warn."""
        config = Config.load(root=tmp_path)
        conductor = tmp_path / "docs" / "project-conductor.md"
        conductor.parent.mkdir(parents=True)
        conductor.write_text("""
## Current Phase
**Phase 9** ⏸️ AWAITING MAINTAINER

## Active Task
| ID | Name |
|----|------|
| 1 | Do thing |
""")
        check = ConductorHealthCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_no_active_and_no_awaiting_warns(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        conductor = tmp_path / "docs" / "project-conductor.md"
        conductor.parent.mkdir(parents=True)
        conductor.write_text("""
## Current Phase
**Phase 1** ✅ COMPLETE

## Active Task
| ID | Name |
|----|------|
| 1 | Do thing |
""")
        check = ConductorHealthCheck()
        issues = check.run(tmp_path, config)
        assert any("No phase marked as ACTIVE" in i.detail for i in issues)


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
        archive.write_text("---\ntype: backlog\ntask_id: FEAT-001\n---\n\n# FEAT-001\n")
        check = ArchiveIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "Invalid type 'backlog'" in issues[0].detail

    def test_filename_mismatch(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        archive = tmp_path / "docs" / "archive" / "FEAT-001-foundation.md"
        archive.parent.mkdir(parents=True)
        archive.write_text("---\ntype: archive\ntask_id: WRONG-ID\n---\n\n# FEAT-001\n")
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

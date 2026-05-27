"""Tests for drift guard engine."""

from pathlib import Path

from drifter.config import Config
from drifter.drift_guard import (
    ConductorHealthCheck,
    CrossDocConsistencyCheck,
    DigestStalenessCheck,
    HardcodedPathCheck,
    StaleReferenceCheck,
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
        report = run_checks(root=tmp_path, config=config)
        assert report.score == 100
        assert report.total == 0

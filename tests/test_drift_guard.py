"""Tests for the drift guard engine."""

from pathlib import Path

from drifter.config import Config
from drifter.drift_guard import run_checks


class TestRunChecks:
    def test_empty_project(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
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
        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text("[git]\nalways_block = [\"git commit\"]\n[shell]\nblocked = []\n")
        agents = tmp_path / "AGENTS.md"
        agents.write_text("# AGENTS.md\n\nRead dangerous_patterns.toml before running commands.\n")
        readme = tmp_path / "README.md"
        readme.write_text(
            "# Project\n"
            "AGENTS.md dangerous_patterns.toml session-protocol.md project-conductor.md\n"
            "drifter check drifter preflight drifter conductor "
            "drifter validate drifter audit drifter init\n"
            "enforcement dangerous_patterns session audit pre-flight conductor\n"
        )
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".env\n")
        report = run_checks(root=tmp_path, config=config)
        assert report.score == 100
        assert report.total == 0

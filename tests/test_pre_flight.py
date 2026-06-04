"""Tests for pre-flight checklist runner."""

from pathlib import Path

from drifter.config import Config
from drifter.pre_flight import run_pre_flight


class TestPreFlight:
    def test_missing_agents_md(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        result = run_pre_flight(root=tmp_path, config=config)
        assert not result.passed
        assert any(
            "AGENTS.md" in step["message"]
            for step in result.step_results
            if not step["passed"]
        )

    def test_all_steps_pass(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        (tmp_path / "AGENTS.md").write_text("# AGENTS\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "session-protocol.md").write_text("---\ntype: playbook\n---\n")
        conductor = docs / "project-conductor.md"
        conductor.write_text(
            "---\ntype: backlog\n---\n"
            "## Current Phase\n**Phase 1** 🟢 ACTIVE\n"
            "## Active Task\n| ID | Name |\n| 1 | Task |\n"
        )
        (tmp_path / "dangerous_patterns.toml").write_text("[git]\nalways_block = []\n")
        result = run_pre_flight(root=tmp_path, config=config)
        assert result.passed
        assert len(result.step_results) == 7

    def test_dangerous_patterns_step_fails(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        (tmp_path / "AGENTS.md").write_text("# AGENTS\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "session-protocol.md").write_text("---\ntype: playbook\n---\n")
        conductor = docs / "project-conductor.md"
        conductor.write_text(
            "---\ntype: backlog\n---\n"
            "## Current Phase\n**Phase 1** 🟢 ACTIVE\n"
            "## Active Task\n| ID | Name |\n| 1 | Task |\n"
        )
        # Missing dangerous_patterns.toml
        result = run_pre_flight(root=tmp_path, config=config)
        assert not result.passed
        assert any(
            "dangerous_patterns.toml" in step["message"] for step in result.step_results
        )

    def test_print_report_no_crash(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        result = run_pre_flight(root=tmp_path, config=config)
        result.print_report()

    def test_keyword_search_no_shell_injection(self, tmp_path: Path) -> None:
        """Malicious keywords must not execute shell commands."""
        config = Config.load(root=tmp_path)
        (tmp_path / "AGENTS.md").write_text("# AGENTS\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "session-protocol.md").write_text("---\ntype: playbook\n---\n")
        conductor = docs / "project-conductor.md"
        conductor.write_text(
            "---\ntype: backlog\n---\n"
            "## Current Phase\n**Phase 1** 🟢 ACTIVE\n"
            "## Active Task\n| ID | Name |\n| 1 | Task |\n"
        )
        (tmp_path / "dangerous_patterns.toml").write_text("[git]\nalways_block = []\n")
        src = tmp_path / "src"
        src.mkdir()
        # A keyword that would be dangerous if passed to shell
        malicious_keyword = "; rm -rf /; "
        result = run_pre_flight(root=tmp_path, config=config, keyword=malicious_keyword)
        # Should complete without crashing or executing shell commands
        assert any(
            step["name"] == "Grep for Existing Code" for step in result.step_results
        )
        # Verify no files were harmed (tmp_path still exists)
        assert tmp_path.exists()

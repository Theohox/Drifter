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

    def test_all_steps_pass(self, pre_flight_project) -> None:
        root = pre_flight_project()
        config = Config.load(root=root)
        result = run_pre_flight(root=root, config=config)
        assert result.passed
        assert len(result.step_results) == 7

    def test_dangerous_patterns_step_fails(self, pre_flight_project) -> None:
        root = pre_flight_project(with_patterns=False)
        config = Config.load(root=root)
        result = run_pre_flight(root=root, config=config)
        assert not result.passed
        assert any(
            "dangerous_patterns.toml" in step["message"] for step in result.step_results
        )

    def test_print_report_no_crash(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        result = run_pre_flight(root=tmp_path, config=config)
        result.print_report()

    def test_keyword_search_no_shell_injection(self, pre_flight_project) -> None:
        """Malicious keywords must not execute shell commands."""
        root = pre_flight_project()
        config = Config.load(root=root)
        (root / "src").mkdir()
        # A keyword that would be dangerous if passed to shell
        malicious_keyword = "; rm -rf /; "
        result = run_pre_flight(root=root, config=config, keyword=malicious_keyword)
        # Should complete without crashing or executing shell commands
        assert any(
            step["name"] == "Grep for Existing Code" for step in result.step_results
        )

    def test_preflight_records_drift_score_in_conductor(
        self, pre_flight_project
    ) -> None:
        """Wiring: preflight appends to the conductor's Drift Score History."""
        from types import SimpleNamespace

        from drifter._cli_admin import cmd_preflight

        root = pre_flight_project(
            conductor_tail=(
                "## Drift Score History\n\n"
                "| Timestamp | Score | Tests | Notes |\n"
                "|-----------|-------|-------|-------|\n"
                "| — | — | — | — |\n"
            )
        )
        conductor = root / "docs" / "project-conductor.md"

        rc = cmd_preflight(SimpleNamespace(root=root, task=None, keyword=None))
        assert rc == 0
        text = conductor.read_text()
        assert "preflight" in text
        assert "/100 |" in text

    def test_task_appears_in_report_header(self, tmp_path: Path, capsys) -> None:
        config = Config.load(root=tmp_path)
        result = run_pre_flight(root=tmp_path, config=config, task="Fix the widget")
        assert result.task == "Fix the widget"
        result.print_report()
        assert "Task: Fix the widget" in capsys.readouterr().out

    def test_task_written_to_session_log(self, tmp_path: Path) -> None:
        """--task is wired: the planned task lands in the session audit log."""
        from types import SimpleNamespace

        from drifter._cli_admin import cmd_preflight
        from drifter.session_logger import SessionLogger

        cmd_preflight(SimpleNamespace(root=tmp_path, task="Ship it", keyword=None))
        entries = SessionLogger(root=tmp_path).read_entries()
        assert any(e.action == "TASK" and e.target == "Ship it" for e in entries)

    def test_no_task_no_log_entry(self, tmp_path: Path) -> None:
        from types import SimpleNamespace

        from drifter._cli_admin import cmd_preflight
        from drifter.session_logger import SessionLogger

        cmd_preflight(SimpleNamespace(root=tmp_path, task=None, keyword=None))
        entries = SessionLogger(root=tmp_path).read_entries()
        assert not any(e.action == "TASK" for e in entries)

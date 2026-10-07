"""Tests for _cli_check command handlers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from drifter._cli_check import cmd_check, cmd_session_report
from drifter.session_logger import SessionLogger


class TestCmdCheck:
    def test_score_output(self, tmp_path: Path, capsys) -> None:
        # Empty project has errors (no conductor, no dangerous_patterns.toml)
        rc = cmd_check(SimpleNamespace(root=tmp_path, score=True))
        out = capsys.readouterr().out
        assert "SCORE:" in out
        assert rc == 1

    def test_json_output_is_structured(self, tmp_path: Path, capsys) -> None:
        import json

        cmd_check(
            SimpleNamespace(root=tmp_path, score=False, json=False, format="json")
        )
        data = json.loads(capsys.readouterr().out)
        assert "score" in data
        assert isinstance(data["issues"], list)

    def test_json_flag_is_alias_for_format_json(self, tmp_path: Path, capsys) -> None:
        import json

        cmd_check(SimpleNamespace(root=tmp_path, score=False, json=True, format=None))
        data = json.loads(capsys.readouterr().out)
        assert "score" in data

    def test_format_json_via_parser(self, tmp_path: Path, capsys) -> None:
        import json

        from drifter.cli import main

        rc = main(["--root", str(tmp_path), "check", "--format", "json"])
        data = json.loads(capsys.readouterr().out)
        assert "score" in data
        assert rc == 1

    def test_github_format(self, tmp_path: Path, capsys) -> None:
        rc = cmd_check(
            SimpleNamespace(root=tmp_path, score=False, json=False, format="github")
        )
        out = capsys.readouterr().out
        assert rc == 1
        # Empty project: conductor_health and dangerous_patterns are errors,
        # readme_completeness and gitignore are warnings
        assert "::error file=project-conductor.md::conductor_health:" in out
        assert "::error file=dangerous_patterns.toml::dangerous_patterns:" in out
        assert "::warning file=README.md::readme_completeness:" in out


class TestCmdSessionReport:
    def test_empty_log_passes(self, tmp_path: Path, capsys) -> None:
        rc = cmd_session_report(SimpleNamespace(root=tmp_path))
        out = capsys.readouterr().out
        assert rc == 0
        assert "SESSION REPORT CARD PASSED" in out

    def test_write_without_read_fails(self, tmp_path: Path, capsys) -> None:
        SessionLogger(root=tmp_path).log("WRITE", "src/main.py")
        rc = cmd_session_report(SimpleNamespace(root=tmp_path))
        out = capsys.readouterr().out
        assert rc == 1
        assert "SESSION REPORT CARD FAILED" in out

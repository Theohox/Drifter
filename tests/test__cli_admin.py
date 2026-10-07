"""Tests for _cli_admin command handlers."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from drifter._cli_admin import (
    cmd_audit,
    cmd_describe,
    cmd_log,
    cmd_log_rotate,
    cmd_manifest,
)
from drifter.session_logger import SessionLogger


class TestCmdLogRotate:
    def test_rotates_existing_log(self, tmp_path: Path) -> None:
        logger = SessionLogger(root=tmp_path)
        logger.log("READ", "foo.py")

        rc = cmd_log_rotate(SimpleNamespace(root=tmp_path))
        assert rc == 0

        fresh = SessionLogger(root=tmp_path)
        assert fresh.read_entries() == []
        archives = list((tmp_path / ".drifter").glob("session.log.*"))
        assert len(archives) == 1

    def test_no_log_returns_zero(self, tmp_path: Path, capsys) -> None:
        rc = cmd_log_rotate(SimpleNamespace(root=tmp_path))
        assert rc == 0
        assert "No session log" in capsys.readouterr().out


class TestCmdLog:
    def test_logs_entry(self, tmp_path: Path) -> None:
        rc = cmd_log(SimpleNamespace(root=tmp_path, action="READ", target="a.py"))
        assert rc == 0
        entries = SessionLogger(root=tmp_path).read_entries()
        assert len(entries) == 1
        assert entries[0].action == "READ"
        assert entries[0].target == "a.py"


class TestCmdAudit:
    def test_missing_patterns_file_fails(self, tmp_path: Path, capsys) -> None:
        rc = cmd_audit(SimpleNamespace(root=tmp_path, window=100, no_history=True))
        assert rc == 1
        assert "dangerous_patterns.toml not found" in capsys.readouterr().out

    def test_no_history_no_violations(self, tmp_path: Path, capsys) -> None:
        (tmp_path / "dangerous_patterns.toml").write_text(
            '[git]\nalways_block = ["git commit"]\n'
        )
        rc = cmd_audit(SimpleNamespace(root=tmp_path, window=100, no_history=True))
        assert rc == 0
        assert "No violations detected" in capsys.readouterr().out

    def test_history_violation_detected(self, tmp_path: Path, capsys) -> None:
        (tmp_path / "dangerous_patterns.toml").write_text(
            '[git]\nalways_block = ["git commit"]\n'
        )
        history = tmp_path / "history"
        history.write_text("git status\ngit commit -m oops\n")
        (tmp_path / "drifter.toml").write_text(
            f'[drifter]\nhistory_path = "{history}"\n'
        )
        rc = cmd_audit(SimpleNamespace(root=tmp_path, window=100, no_history=False))
        out = capsys.readouterr().out
        assert rc == 1
        assert "1 VIOLATION(S) FOUND" in out
        assert "git commit -m oops" in out


class TestCmdManifest:
    def test_writes_manifest(self, fake_project, capsys) -> None:
        root = fake_project(version="0.4.0")
        rc = cmd_manifest(SimpleNamespace(root=root))
        assert rc == 0
        assert "Capability manifest written" in capsys.readouterr().out
        manifest = root / ".drifter" / "capability-manifest.json"
        assert '"version": "0.4.0"' in manifest.read_text()


class TestCmdDescribe:
    def test_json_format(self, fake_project, capsys) -> None:
        root = fake_project(version="0.4.0")
        rc = cmd_describe(SimpleNamespace(root=root, format="json"))
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["version"] == "0.4.0"
        assert "commands" in data

    def test_markdown_format(self, fake_project, capsys) -> None:
        root = fake_project(version="0.4.0")
        rc = cmd_describe(SimpleNamespace(root=root, format="markdown"))
        assert rc == 0
        assert "# Drifter 0.4.0" in capsys.readouterr().out

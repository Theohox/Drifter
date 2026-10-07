"""Tests for _cli_conductor command handlers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from drifter._cli_conductor import cmd_conductor
from drifter.cli import main

CONDUCTOR = (
    "---\ntype: backlog\n---\n"
    "## Current Phase\n**Phase 1** 🟢 ACTIVE\n"
    "## Active Task\n\n"
    "| Field | Value |\n"
    "|-------|-------|\n"
    "| **ID** | FEAT-001 |\n"
    "| **Name** | Task One |\n"
    "| **Status** | 🟡 IN PROGRESS |\n"
    "| **Pipeline** | active |\n"
    "| **Depends On** | — |\n"
    "| **Evidence** | proof |\n"
    "| **Next** | — |\n"
    "## Blocked Tasks\n"
    "| ID | Name | Blocked On |\n"
    "## Future Tasks\n"
    "## Completed Tasks\n"
    "## Drift Score History\n\n"
    "| Timestamp | Score | Tests | Notes |\n"
    "|-----------|-------|-------|-------|\n"
    "| — | — | — | — |\n"
)


def _fixture(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    conductor = docs / "project-conductor.md"
    conductor.write_text(CONDUCTOR)
    return conductor


class TestParser:
    def test_unknown_command_rejected_by_argparse(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["conductor", "bogus"])
        assert exc_info.value.code == 2


class TestBranches:
    def test_init_creates_conductor(self, tmp_path: Path, capsys) -> None:
        rc = cmd_conductor(
            SimpleNamespace(root=tmp_path, conductor_command="init", force=False)
        )
        assert rc == 0
        assert "initialized" in capsys.readouterr().out

    def test_show_prints_active_task(self, tmp_path: Path, capsys) -> None:
        _fixture(tmp_path)
        rc = cmd_conductor(SimpleNamespace(root=tmp_path, conductor_command="show"))
        out = capsys.readouterr().out
        assert rc == 0
        assert "Task One" in out

    def test_done_requires_task_id(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["conductor", "done"])
        assert exc_info.value.code == 2

    def test_done_marks_task(self, tmp_path: Path, capsys) -> None:
        _fixture(tmp_path)
        rc = cmd_conductor(
            SimpleNamespace(
                root=tmp_path,
                conductor_command="done",
                task_id="FEAT-001",
                evidence="proof",
            )
        )
        assert rc == 0
        assert "marked as done" in capsys.readouterr().out

    def test_block_requires_reason(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["conductor", "block", "--task-id", "FEAT-002"])
        assert exc_info.value.code == 2

    def test_next_prints_hint(self, tmp_path: Path, capsys) -> None:
        _fixture(tmp_path)
        rc = cmd_conductor(SimpleNamespace(root=tmp_path, conductor_command="next"))
        assert rc == 0

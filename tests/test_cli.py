"""Tests for CLI commands."""

from pathlib import Path
from unittest.mock import MagicMock

from drifter.cli import cmd_init


class TestCmdInit:
    def test_creates_all_files(self, tmp_path: Path) -> None:
        args = MagicMock()
        args.root = str(tmp_path)
        args.force = False
        cmd_init(args)
        assert (tmp_path / "AGENTS.md").exists()
        assert (tmp_path / "dangerous_patterns.toml").exists()
        assert (tmp_path / "docs" / "session-protocol.md").exists()
        assert (tmp_path / "docs" / "project-conductor.md").exists()
        assert (tmp_path / "docs" / "archive").is_dir()

    def test_mentions_all_canonical_files(self, tmp_path: Path) -> None:
        args = MagicMock()
        args.root = str(tmp_path)
        args.force = False
        import io
        import sys

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            cmd_init(args)
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        assert "AGENTS.md" in output
        assert "dangerous_patterns.toml" in output
        assert "session-protocol.md" in output
        assert "project-conductor.md" in output

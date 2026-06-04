"""Tests for the plugin interceptor API."""

from pathlib import Path

import pytest

from drifter.plugin_api import ToolInterceptor
from drifter.session_logger import SessionLogger


class TestToolInterceptor:
    def test_before_read_logs_and_returns_none(self, tmp_path: Path) -> None:
        interceptor = ToolInterceptor(root=tmp_path)
        result = interceptor.before_read("test.py")
        assert result is None
        logger = SessionLogger(root=tmp_path)
        entries = logger.read_entries()
        assert any(e.action == "READ" and e.target == "test.py" for e in entries)

    def test_before_write_logs_and_returns_none(self, tmp_path: Path) -> None:
        interceptor = ToolInterceptor(root=tmp_path)
        result = interceptor.before_write("test.py")
        assert result is None
        logger = SessionLogger(root=tmp_path)
        entries = logger.read_entries()
        assert any(e.action == "WRITE" and e.target == "test.py" for e in entries)

    def test_before_shell_enforce_blocks(self, tmp_path: Path) -> None:
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text('[git]\nalways_block = ["git commit"]\n')
        interceptor = ToolInterceptor(root=tmp_path)

        from drifter.errors import DangerousCommandError

        with pytest.raises(DangerousCommandError):
            interceptor.before_shell("git commit -m x")

    def test_before_shell_returns_classification_on_allow(self, tmp_path: Path) -> None:
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text('[git]\nallowed = ["git status"]\n')
        interceptor = ToolInterceptor(root=tmp_path)

        classification = interceptor.before_shell("git status")
        assert classification.action == "allow"

    def test_before_shell_logs_shell_action(self, tmp_path: Path) -> None:
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text('[git]\nallowed = ["git status"]\n')
        interceptor = ToolInterceptor(root=tmp_path)

        interceptor.before_shell("git status")
        logger = SessionLogger(root=tmp_path)
        entries = logger.read_entries()
        assert any(e.action == "SHELL" and e.target == "git status" for e in entries)

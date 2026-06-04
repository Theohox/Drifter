"""Tests for cross-platform shell history reader."""

from __future__ import annotations

from pathlib import Path

import pytest

from drifter.history_reader import HistoryReader


class TestHistoryReaderBash:
    def test_parse_plain_lines(self, tmp_path: Path) -> None:
        hist = tmp_path / ".bash_history"
        hist.write_text("echo hello\nls -la\ncd /tmp\n", encoding="utf-8")
        reader = HistoryReader(hist)
        assert reader.shell == "bash"
        cmds = reader.read_commands()
        assert cmds == ["echo hello", "ls -la", "cd /tmp"]

    def test_max_entries(self, tmp_path: Path) -> None:
        hist = tmp_path / ".bash_history"
        hist.write_text("a\nb\nc\nd\n", encoding="utf-8")
        reader = HistoryReader(hist)
        assert reader.read_commands(max_entries=2) == ["c", "d"]

    def test_empty_file(self, tmp_path: Path) -> None:
        hist = tmp_path / ".bash_history"
        hist.write_text("", encoding="utf-8")
        reader = HistoryReader(hist)
        assert reader.read_commands() == []

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        hist = tmp_path / ".bash_history"
        reader = HistoryReader(hist)
        assert reader.read_commands() == []


class TestHistoryReaderZsh:
    def test_parse_with_timestamps(self, tmp_path: Path) -> None:
        hist = tmp_path / ".zsh_history"
        hist.write_text(
            ": 1234567890:0;echo hello\n: 1234567891:0;ls -la\n", encoding="utf-8"
        )
        reader = HistoryReader(hist)
        assert reader.shell == "zsh"
        cmds = reader.read_commands()
        assert cmds == ["echo hello", "ls -la"]

    def test_parse_without_timestamps(self, tmp_path: Path) -> None:
        hist = tmp_path / ".zsh_history"
        hist.write_text("echo hello\nls -la\n", encoding="utf-8")
        reader = HistoryReader(hist)
        cmds = reader.read_commands()
        assert cmds == ["echo hello", "ls -la"]

    def test_mixed_format(self, tmp_path: Path) -> None:
        hist = tmp_path / ".zsh_history"
        hist.write_text(": 1234567890:0;echo hello\nls -la\n", encoding="utf-8")
        reader = HistoryReader(hist)
        cmds = reader.read_commands()
        assert cmds == ["echo hello", "ls -la"]


class TestHistoryReaderFish:
    def test_parse_yaml_like(self, tmp_path: Path) -> None:
        hist = tmp_path / "fish_history"
        hist.write_text(
            "- cmd: echo hello\n  when: 1234567890\n- cmd: ls -la\n  when: 1234567891\n",
            encoding="utf-8",
        )
        reader = HistoryReader(hist)
        assert reader.shell == "fish"
        cmds = reader.read_commands()
        assert cmds == ["echo hello", "ls -la"]

    def test_parse_from_content_heuristic(self, tmp_path: Path) -> None:
        hist = tmp_path / "some_history"
        hist.write_text(
            "- cmd: echo hello\n  when: 1234567890\n",
            encoding="utf-8",
        )
        reader = HistoryReader(hist)
        assert reader.shell == "fish"


class TestHistoryReaderAutoDetect:
    def test_from_shell_env_bash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bash_hist = tmp_path / ".bash_history"
        bash_hist.write_text("echo hello\n", encoding="utf-8")
        monkeypatch.setenv("SHELL", "/bin/bash")
        monkeypatch.setenv("HOME", str(tmp_path))
        reader = HistoryReader.auto_detect()
        assert reader is not None
        assert reader.shell == "bash"
        assert reader.read_commands() == ["echo hello"]

    def test_from_shell_env_zsh(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        zsh_hist = tmp_path / ".zsh_history"
        zsh_hist.write_text("ls\n", encoding="utf-8")
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.setenv("HOME", str(tmp_path))
        reader = HistoryReader.auto_detect()
        assert reader is not None
        assert reader.shell == "zsh"

    def test_from_shell_env_fish(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fish_dir = tmp_path / ".local/share/fish"
        fish_dir.mkdir(parents=True)
        fish_hist = fish_dir / "fish_history"
        fish_hist.write_text("- cmd: echo hello\n  when: 1\n", encoding="utf-8")
        monkeypatch.setenv("SHELL", "/usr/bin/fish")
        monkeypatch.setenv("HOME", str(tmp_path))
        reader = HistoryReader.auto_detect()
        assert reader is not None
        assert reader.shell == "fish"

    def test_from_explicit_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        hist = tmp_path / "custom_history"
        hist.write_text("echo hi\n", encoding="utf-8")
        monkeypatch.setenv("DRIFTER_HISTORY_PATH", str(hist))
        reader = HistoryReader.auto_detect()
        assert reader is not None
        assert reader.path == hist

    def test_no_history_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("DRIFTER_HISTORY_PATH", raising=False)
        monkeypatch.delenv("SHELL", raising=False)
        reader = HistoryReader.auto_detect()
        assert reader is None

    def test_fallback_order(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If SHELL is unset, fall back to first existing known path."""
        bash_hist = tmp_path / ".bash_history"
        bash_hist.write_text("echo hello\n", encoding="utf-8")
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("SHELL", raising=False)
        monkeypatch.delenv("DRIFTER_HISTORY_PATH", raising=False)
        reader = HistoryReader.auto_detect()
        assert reader is not None
        assert reader.shell == "bash"

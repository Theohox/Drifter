"""Tests for session logger."""

from pathlib import Path

from drifter.session_logger import SessionLogger


class TestSessionLogger:
    def test_log_and_read(self, tmp_path: Path) -> None:
        log_file = tmp_path / "session.log"
        logger = SessionLogger(path=log_file)
        logger.log("READ", "src/foo.py")
        logger.log("WRITE", "src/bar.py")
        entries = logger.read_entries()
        assert len(entries) == 2
        assert entries[0].action == "READ"
        assert entries[0].target == "src/foo.py"
        assert entries[1].action == "WRITE"
        assert entries[1].target == "src/bar.py"

    def test_clear(self, tmp_path: Path) -> None:
        log_file = tmp_path / "session.log"
        logger = SessionLogger(path=log_file)
        logger.log("READ", "src/foo.py")
        logger.clear()
        entries = logger.read_entries()
        assert len(entries) == 0

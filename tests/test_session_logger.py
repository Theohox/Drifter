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
        assert entries[0].verified is True
        assert entries[0].pid > 0
        assert entries[1].action == "WRITE"
        assert entries[1].target == "src/bar.py"
        assert entries[1].verified is True

    def test_rotate_log(self, tmp_path: Path) -> None:
        log_file = tmp_path / "session.log"
        logger = SessionLogger(path=log_file)
        logger.log("READ", "src/foo.py")
        archive = logger.rotate_log()
        assert archive is not None
        assert archive.exists()
        assert not log_file.exists()
        # New log is empty
        assert logger.read_entries() == []

    def test_rotate_empty_log(self, tmp_path: Path) -> None:
        log_file = tmp_path / "session.log"
        logger = SessionLogger(path=log_file)
        archive = logger.rotate_log()
        assert archive is None

    def test_tampered_entry_skipped(self, tmp_path: Path) -> None:
        log_file = tmp_path / "session.log"
        logger = SessionLogger(path=log_file)
        logger.log("READ", "src/foo.py")
        # Tamper with the log
        text = log_file.read_text(encoding="utf-8")
        tampered = text.replace("src/foo.py", "src/evil.py")
        log_file.write_text(tampered, encoding="utf-8")
        entries = logger.read_entries()
        # Tampered entry should be skipped
        assert len(entries) == 0

    def test_legacy_format_fallback(self, tmp_path: Path) -> None:
        log_file = tmp_path / "session.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text(
            "[2026-01-01T00:00:00+00:00] READ src/legacy.py\n", encoding="utf-8"
        )
        logger = SessionLogger(path=log_file)
        entries = logger.read_entries()
        assert len(entries) == 1
        assert entries[0].action == "READ"
        assert entries[0].target == "src/legacy.py"
        assert entries[0].verified is False

    def test_file_permissions(self, tmp_path: Path) -> None:
        import os
        import stat

        if os.name == "nt":
            return  # Skip on Windows

        log_file = tmp_path / "session.log"
        logger = SessionLogger(path=log_file)
        logger.log("READ", "src/foo.py")

        # Directory should be 0o700
        dir_mode = log_file.parent.stat().st_mode
        assert stat.S_IMODE(dir_mode) == 0o700

        # Log file should be 0o600
        file_mode = log_file.stat().st_mode
        assert stat.S_IMODE(file_mode) == 0o600

        # Secret file should be 0o600
        secret = log_file.parent / ".session_secret"
        assert secret.exists()
        secret_mode = secret.stat().st_mode
        assert stat.S_IMODE(secret_mode) == 0o600

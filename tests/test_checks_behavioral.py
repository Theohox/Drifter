"""Tests for session behavioral audit checks."""

from pathlib import Path

from drifter.config import Config
from drifter.checks.behavioral import (
    DriftCheckAfterWriteCheck,
    NoRushCheck,
    ReadBeforeWriteCheck,
    TestAfterWriteCheck,
)
from drifter.session_logger import SessionLogger


class TestNoRushCheck:
    def test_zero_writes_no_issue(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        # No entries
        check = NoRushCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_zero_drift_checks_error(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        for i in range(3):
            logger.log("WRITE", f"file{i}.py")
        check = NoRushCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "zero" in issues[0].detail

    def test_ratio_4_to_1_warns(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        for i in range(4):
            logger.log("WRITE", f"file{i}.py")
        logger.log("SHELL", "drifter check")
        check = NoRushCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert issues[0].severity == "warn"
        assert "4:1" in issues[0].detail or "ratio" in issues[0].detail

    def test_ratio_under_3_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        for i in range(3):
            logger.log("WRITE", f"file{i}.py")
        logger.log("SHELL", "drifter check")
        check = NoRushCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_ratio_11_to_1_errors(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        for i in range(11):
            logger.log("WRITE", f"file{i}.py")
        logger.log("SHELL", "drifter check")
        check = NoRushCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "severe" in issues[0].detail or "11" in issues[0].detail

    def test_check_action_counts(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        for i in range(5):
            logger.log("WRITE", f"file{i}.py")
        logger.log("CHECK", "drifter check")
        check = NoRushCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert issues[0].severity == "warn"


class TestReadBeforeWriteCheck:
    def test_write_without_read_detected(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        logger.log("WRITE", "src/main.py")
        check = ReadBeforeWriteCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "WRITE src/main.py without preceding READ" in issues[0].detail
        assert issues[0].severity == "error"

    def test_write_after_read_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        logger.log("READ", "src/main.py")
        logger.log("WRITE", "src/main.py")
        check = ReadBeforeWriteCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_read_after_write_still_passes(self, tmp_path: Path) -> None:
        """Two-pass approach: READ anywhere in log satisfies check."""
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        logger.log("WRITE", "src/main.py")
        logger.log("READ", "src/main.py")
        check = ReadBeforeWriteCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_duplicate_write_only_one_issue(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        logger.log("WRITE", "src/main.py")
        logger.log("WRITE", "src/main.py")
        check = ReadBeforeWriteCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1

    def test_empty_log_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        check = ReadBeforeWriteCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestTestAfterWriteCheck:
    def test_write_not_followed_by_test(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        logger.log("WRITE", "src/main.py")
        check = TestAfterWriteCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "Last WRITE not followed by a test run" in issues[0].detail
        assert issues[0].severity == "error"

    def test_write_followed_by_test_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        logger.log("WRITE", "src/main.py")
        logger.log("SHELL", "python3 -m pytest tests/ -q")
        check = TestAfterWriteCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_pytest_in_target_counts(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        logger.log("WRITE", "src/main.py")
        logger.log("SHELL", "pytest")
        check = TestAfterWriteCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_empty_log_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        check = TestAfterWriteCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_no_writes_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        logger.log("SHELL", "pytest")
        check = TestAfterWriteCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestDriftCheckAfterWriteCheck:
    def test_write_not_followed_by_drift_check(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        logger.log("WRITE", "src/main.py")
        check = DriftCheckAfterWriteCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "Last WRITE not followed by 'drifter check'" in issues[0].detail
        assert issues[0].severity == "error"

    def test_write_followed_by_shell_drift_check_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        logger.log("WRITE", "src/main.py")
        logger.log("SHELL", "drifter check")
        check = DriftCheckAfterWriteCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_write_followed_by_check_action_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        logger.log("WRITE", "src/main.py")
        logger.log("CHECK", "drifter check passed 100/100")
        check = DriftCheckAfterWriteCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_empty_log_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        check = DriftCheckAfterWriteCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_no_writes_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        logger = SessionLogger(root=tmp_path)
        logger.log("SHELL", "drifter check")
        check = DriftCheckAfterWriteCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

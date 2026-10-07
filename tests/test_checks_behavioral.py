"""Tests for session behavioral audit checks."""

from pathlib import Path

from drifter.checks.behavioral import (
    DriftCheckAfterWriteCheck,
    NoRushCheck,
    ReadBeforeWriteCheck,
    TestAfterWriteCheck,
    is_drift_check,
    is_test_run,
)
from drifter.config import Config
from drifter.session_logger import SessionLogger


class TestEvidenceMatching:
    def test_cat_pytest_ini_is_not_a_test_run(self) -> None:
        assert not is_test_run("SHELL", "cat pytest.ini")

    def test_echo_drifter_check_is_not_a_drift_check(self) -> None:
        assert not is_drift_check("SHELL", "echo drifter check")

    def test_real_invocations_count(self) -> None:
        assert is_test_run("SHELL", "pytest")
        assert is_test_run("SHELL", ".venv/bin/python -m pytest tests/ -q")
        assert is_test_run("SHELL", "ruff check src/ && python3 -m pytest")
        assert is_drift_check("SHELL", "drifter check")
        assert is_drift_check("SHELL", ".venv/bin/python -m drifter check")
        assert is_drift_check("CHECK", "drifter check passed 100/100")

    def test_mentions_in_arguments_do_not_count(self) -> None:
        assert not is_test_run("SHELL", "grep -r pytest src/")
        assert not is_drift_check("SHELL", "git log --grep='drifter check'")


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
        assert "4 WRITEs vs 1 drift checks (ratio 4.0:1) — max 3:1" in issues[0].detail

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
        assert (
            "11 WRITEs vs 1 drift checks (ratio 11.0:1) — severe rushing (max 3:1)"
            in issues[0].detail
        )

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

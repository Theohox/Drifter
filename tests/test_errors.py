"""Tests for enforcement exception classes."""

from drifter.errors import DangerousCommandError, ApprovalRequiredError, DrifterError
from drifter.shell_guard import Classification


class TestDrifterError:
    def test_base_class_attributes(self) -> None:
        classification = Classification(action="block", reason="test", matched_pattern="git commit")
        exc = DrifterError("git commit", "git commit", "blocked by policy", classification)
        assert exc.command == "git commit"
        assert exc.pattern == "git commit"
        assert exc.reason == "blocked by policy"
        assert exc.classification == classification
        assert "DrifterError" in str(exc)


class TestDangerousCommandError:
    def test_stores_command_and_pattern(self) -> None:
        classification = Classification(action="block", reason="test", matched_pattern="git commit")
        exc = DangerousCommandError("git commit", "git commit", "blocked by policy", classification)
        assert exc.command == "git commit"
        assert exc.pattern == "git commit"
        assert "blocked by policy" in str(exc)
        assert exc.classification == classification

    def test_is_instance_of_drifter_error(self) -> None:
        classification = Classification(action="block", reason="test")
        exc = DangerousCommandError("rm -rf /", "rm -rf /", "Blocked dangerous command", classification)
        assert isinstance(exc, DrifterError)


class TestApprovalRequiredError:
    def test_stores_command(self) -> None:
        classification = Classification(action="approval_required", reason="test", matched_pattern="git add")
        exc = ApprovalRequiredError("git add file.py", "git add", "requires approval", classification)
        assert exc.command == "git add file.py"
        assert "requires approval" in str(exc)
        assert exc.classification == classification

    def test_is_instance_of_drifter_error(self) -> None:
        classification = Classification(action="approval_required", reason="test")
        exc = ApprovalRequiredError("git add", "git add", "requires approval", classification)
        assert isinstance(exc, DrifterError)

"""Tests for enforcement exception classes."""

from drifter.errors import DangerousCommandError, ApprovalRequiredError
from drifter.shell_guard import Classification


class TestDangerousCommandError:
    def test_stores_command_and_pattern(self) -> None:
        classification = Classification(action="block", reason="test", matched_pattern="git commit")
        exc = DangerousCommandError("git commit", "git commit", "blocked by policy", classification)
        assert exc.command == "git commit"
        assert exc.pattern == "git commit"
        assert "blocked by policy" in str(exc)
        assert exc.classification == classification

    def test_default_reason(self) -> None:
        classification = Classification(action="block", reason="test", matched_pattern="rm -rf /")
        exc = DangerousCommandError("rm -rf /", "rm -rf /", "Blocked dangerous command", classification)
        assert "Blocked dangerous command" in str(exc)
        assert exc.command == "rm -rf /"


class TestApprovalRequiredError:
    def test_stores_command(self) -> None:
        classification = Classification(action="approval_required", reason="test", matched_pattern="git add")
        exc = ApprovalRequiredError("git add file.py", "git add", "requires approval", classification)
        assert exc.command == "git add file.py"
        assert "requires approval" in str(exc)
        assert exc.classification == classification

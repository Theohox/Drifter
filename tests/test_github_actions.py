"""Tests for GitHub Actions reporter."""

from drifter.drift_guard import Issue
from drifter.reporters.github_actions import GitHubActionsReporter


class TestGitHubActionsReporter:
    def test_error_annotation(self) -> None:
        reporter = GitHubActionsReporter()
        issues = [
            Issue(check="test", file="foo.py", detail="broken", severity="error"),
        ]
        output = reporter.report(issues)
        assert "::error file=foo.py::" in output
        assert "broken" in output

    def test_warning_annotation(self) -> None:
        reporter = GitHubActionsReporter()
        issues = [
            Issue(check="test", file="bar.py", detail="stale", severity="warn"),
        ]
        output = reporter.report(issues)
        assert "::warning file=bar.py::" in output
        assert "stale" in output

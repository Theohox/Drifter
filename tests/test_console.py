"""Tests for console reporter."""

from drifter.drift_guard import Issue
from drifter.reporters.console import ConsoleReporter


class TestConsoleReporter:
    def test_report_formats_issues(self) -> None:
        reporter = ConsoleReporter()
        issues = [
            Issue(check="test", file="foo.py", detail="something wrong", severity="error"),
            Issue(check="test2", file="bar.py", detail="warning here", severity="warn"),
        ]
        output = reporter.report(issues)
        assert "foo.py" in output
        assert "something wrong" in output
        assert "bar.py" in output

    def test_empty_issues(self) -> None:
        reporter = ConsoleReporter()
        output = reporter.report([])
        assert output == ""

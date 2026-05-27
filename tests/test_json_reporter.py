"""Tests for JSON reporter."""

import json

from drifter.drift_guard import Issue
from drifter.reporters.json_reporter import JsonReporter


class TestJsonReporter:
    def test_report_is_valid_json(self) -> None:
        reporter = JsonReporter()
        issues = [
            Issue(check="test", file="foo.py", detail="something wrong", severity="error"),
        ]
        output = reporter.report(issues)
        data = json.loads(output)
        assert len(data) == 1
        assert data[0]["check"] == "test"

    def test_empty_issues(self) -> None:
        reporter = JsonReporter()
        output = reporter.report([])
        assert json.loads(output) == []

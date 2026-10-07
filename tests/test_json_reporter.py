"""Tests for JSON reporter."""

import json

from drifter.checks._base import Issue
from drifter.reporters.json_reporter import JsonReporter


class TestJsonReporter:
    def test_report_is_valid_json_with_structured_issues(self) -> None:
        reporter = JsonReporter()
        issues = [
            Issue(
                check="test", file="foo.py", detail="something wrong", severity="error"
            ),
        ]
        meta = {"score": 90, "total": 1, "errors": 1, "warns": 0, "infos": 0}
        output = reporter.report(issues, meta)
        data = json.loads(output)
        assert data["score"] == 90
        assert len(data["issues"]) == 1
        assert data["issues"][0]["check"] == "test"
        assert data["issues"][0]["severity"] == "error"

    def test_empty_issues(self) -> None:
        reporter = JsonReporter()
        output = reporter.report([])
        assert json.loads(output)["issues"] == []

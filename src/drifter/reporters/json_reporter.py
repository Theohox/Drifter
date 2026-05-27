"""JSON reporter for machine-parseable output."""

from __future__ import annotations

import json

from drifter.checks._base import Issue


class JsonReporter:
    name = "json"

    def report(self, issues: list[Issue]) -> str:
        data = [
            {
                "check": i.check,
                "file": i.file,
                "detail": i.detail,
                "severity": i.severity,
            }
            for i in issues
        ]
        return json.dumps(data, indent=2)

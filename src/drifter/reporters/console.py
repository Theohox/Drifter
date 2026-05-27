"""Console reporter for human-readable output."""

from __future__ import annotations

from drifter.checks._base import Issue


class ConsoleReporter:
    name = "console"

    def report(self, issues: list[Issue]) -> str:
        lines = []
        for issue in issues:
            icon = "✗" if issue.severity == "error" else "⚠" if issue.severity == "warn" else "ℹ"
            lines.append(f"  {icon} [{issue.severity.upper()}] {issue.check}: {issue.file}")
            lines.append(f"     → {issue.detail}")
        return "\n".join(lines)

"""GitHub Actions reporter for CI annotations."""

from __future__ import annotations

from drifter.drift_guard import Issue


class GitHubActionsReporter:
    name = "github"

    def report(self, issues: list[Issue]) -> str:
        lines = []
        for issue in issues:
            level = "error" if issue.severity == "error" else "warning"
            lines.append(f"::{level} file={issue.file}::{issue.check}: {issue.detail}")
        return "\n".join(lines)

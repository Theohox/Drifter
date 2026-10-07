"""Console reporter for human-readable output."""

from __future__ import annotations

from drifter.checks._base import Issue


class ConsoleReporter:
    name = "console"

    def report(self, issues: list[Issue], meta: dict | None = None) -> str:
        meta = meta or {}
        lines = [f"\n{'=' * 60}", "  DRIFT GUARD REPORT", f"{'=' * 60}"]
        score = meta.get("score")
        if score is not None:
            lines.append(f"  Score: {score}/100")
        lines.append(f"  Issues: {len(issues)}")
        lines.append(f"{'=' * 60}")

        if issues:
            errors = [i for i in issues if i.severity == "error"]
            warns = [i for i in issues if i.severity == "warn"]
            infos = [i for i in issues if i.severity == "info"]
            if errors:
                lines.append(f"\n  Errors ({len(errors)}):")
                lines.extend(f"    ✗ {issue}" for issue in errors)
            if warns:
                lines.append(f"\n  Warnings ({len(warns)}):")
                lines.extend(f"    • {issue}" for issue in warns)
            if infos:
                lines.append(f"\n  Info ({len(infos)}):")
                lines.extend(f"    ℹ {issue}" for issue in infos)
        else:
            lines.append("\n  ✓ No drift detected. System is clean.")

        lines.append(f"{'=' * 60}\n")
        return "\n".join(lines)

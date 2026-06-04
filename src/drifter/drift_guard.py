"""Drift Guard — Universal drift detection engine.

Scans a project for drift between code, docs, and project state.
Plugin-based: each check is a self-contained callable.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from drifter.checks._base import Check, Issue
from drifter.checks import BUILTIN_CHECKS
from drifter.config import Config


@dataclass
class Report:
    score: int
    total: int
    errors: int
    warns: int
    infos: int
    health: str = "excellent"
    issues: list[Issue] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __repr__(self) -> str:
        return (
            f"Report(score={self.score}, total={self.total}, "
            f"errors={self.errors}, warns={self.warns}, health={self.health})"
        )


def run_checks(root: Path | None = None, config: Config | None = None) -> Report:
    """Run all enabled checks and return a report."""
    if config is None:
        config = Config.load(root)
    if root is None:
        root = config.root

    all_issues: list[Issue] = []

    checks_to_run: list[Check] = []
    for check_cfg in config.checks:
        if not check_cfg.enabled:
            continue
        if check_cfg.name in BUILTIN_CHECKS:
            checks_to_run.append(BUILTIN_CHECKS[check_cfg.name]())

    if len(checks_to_run) > 1:
        with ThreadPoolExecutor(max_workers=min(len(checks_to_run), 4)) as executor:
            futures = [executor.submit(check.run, root, config) for check in checks_to_run]
            for future in futures:
                try:
                    all_issues.extend(future.result())
                except Exception as e:
                    all_issues.append(Issue(
                        check="engine",
                        file="drift_guard.py",
                        detail=f"Check failed with exception: {e}",
                        severity="error",
                    ))
    else:
        for check in checks_to_run:
            try:
                all_issues.extend(check.run(root, config))
            except Exception as e:
                all_issues.append(Issue(
                    check="engine",
                    file="drift_guard.py",
                    detail=f"Check failed with exception: {e}",
                    severity="error",
                ))

    errors = sum(1 for i in all_issues if i.severity == "error")
    warns = sum(1 for i in all_issues if i.severity == "warn")
    infos = sum(1 for i in all_issues if i.severity == "info")
    total = len(all_issues)

    error_weight = min(errors, 10)
    warn_weight = min(warns, 25)
    score = max(0, 100 - error_weight * 10 - warn_weight * 2)

    if errors == 0 and warns == 0:
        health = "excellent"
    elif errors == 0:
        health = "good"
    elif score >= 50:
        health = "degraded"
    else:
        health = "critical"

    return Report(
        score=score,
        total=total,
        errors=errors,
        warns=warns,
        infos=infos,
        health=health,
        issues=all_issues,
    )

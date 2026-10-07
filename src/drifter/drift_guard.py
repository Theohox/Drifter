"""Drift Guard — Universal drift detection engine.

Scans a project for drift between code, docs, and project state.
Plugin-based: each check is a self-contained callable.
"""

from __future__ import annotations

import importlib.util
import inspect
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from drifter.checks import BUILTIN_CHECKS
from drifter.checks._base import Check, Issue
from drifter.config import CheckConfig, Config

_SEVERITY_RANK = {"info": 0, "warn": 1, "error": 2}


def _cap_severity(issues: list[Issue], check_cfg: CheckConfig) -> list[Issue]:
    """Demote issues above the configured severity ceiling for this check."""
    cap = _SEVERITY_RANK.get(check_cfg.severity)
    if cap is None:
        return issues
    return [
        issue
        if _SEVERITY_RANK.get(issue.severity, 1) <= cap
        else replace(issue, severity=check_cfg.severity)
        for issue in issues
    ]


def _run_one(
    check: Check, check_cfg: CheckConfig, root: Path, config: Config
) -> list[Issue]:
    """Run one check; a crashing check becomes an error issue, not a crash."""
    try:
        return _cap_severity(check.run(root, config), check_cfg)
    except Exception as e:
        return [
            Issue(
                check=check_cfg.name,
                file="drift_guard.py",
                detail=f"Check failed with exception: {e}",
                severity="error",
            )
        ]


def _load_custom_check(check_cfg: CheckConfig, root: Path) -> Check | Issue:
    """Load a custom check from the file named by the config entry's ``path``.

    Contract: the file must define exactly one check class — a class with a
    ``run(root, config)`` method. It is instantiated with no arguments; if the
    instance has no ``name``, the configured check name is assigned.
    Returns an error Issue instead of raising on any failure.
    """
    path_str = check_cfg.path or ""
    path = Path(path_str)
    if not path.is_absolute():
        path = root / path

    def _error(detail: str) -> Issue:
        return Issue(
            check=check_cfg.name, file=path_str, detail=detail, severity="error"
        )

    if not path.is_file():
        return _error(f"Custom check file not found: {path}")
    spec = importlib.util.spec_from_file_location(
        f"drifter_custom_{check_cfg.name}", path
    )
    if spec is None or spec.loader is None:
        return _error(f"Cannot import custom check from {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        return _error(f"Custom check failed to import: {e}")
    candidates = [
        obj
        for obj in vars(module).values()
        if inspect.isclass(obj)
        and obj.__module__ == module.__name__
        and hasattr(obj, "run")
    ]
    if len(candidates) != 1:
        return _error(
            "Custom check module must define exactly one check class "
            f"with a run() method (found {len(candidates)})"
        )
    try:
        instance = cast(Check, candidates[0]())
    except Exception as e:
        return _error(f"Custom check failed to instantiate: {e}")
    if not getattr(instance, "name", None):
        instance.name = check_cfg.name
    return instance


@dataclass
class Report:
    score: int
    total: int
    errors: int
    warns: int
    infos: int
    issues: list[Issue] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __repr__(self) -> str:
        return (
            f"Report(score={self.score}, total={self.total}, "
            f"errors={self.errors}, warns={self.warns})"
        )


def run_checks(root: Path | None = None, config: Config | None = None) -> Report:
    """Run all enabled checks and return a report."""
    if config is None:
        config = Config.load(root)
    if root is None:
        root = config.root

    all_issues: list[Issue] = []

    checks_to_run: list[tuple[Check, CheckConfig]] = []
    for check_cfg in config.checks:
        if not check_cfg.enabled:
            continue
        if check_cfg.name in BUILTIN_CHECKS:
            checks_to_run.append((BUILTIN_CHECKS[check_cfg.name](), check_cfg))
            if check_cfg.path:
                all_issues.append(
                    Issue(
                        check=check_cfg.name,
                        file=check_cfg.path,
                        detail=(
                            f"Check '{check_cfg.name}' collides with a builtin — "
                            "the builtin wins; 'path' is ignored"
                        ),
                        severity="warn",
                    )
                )
        elif check_cfg.path:
            loaded = _load_custom_check(check_cfg, root)
            if isinstance(loaded, Issue):
                all_issues.append(loaded)
            else:
                checks_to_run.append((loaded, check_cfg))
        else:
            all_issues.append(
                Issue(
                    check=check_cfg.name,
                    file="drifter.toml",
                    detail=(
                        f"Unknown check '{check_cfg.name}' in config — "
                        "no builtin, no path"
                    ),
                    severity="warn",
                )
            )

    if len(checks_to_run) > 1:
        with ThreadPoolExecutor(max_workers=min(len(checks_to_run), 4)) as executor:
            futures = [
                executor.submit(_run_one, check, check_cfg, root, config)
                for check, check_cfg in checks_to_run
            ]
            for future in futures:
                all_issues.extend(future.result())
    else:
        for check, check_cfg in checks_to_run:
            all_issues.extend(_run_one(check, check_cfg, root, config))

    errors = sum(1 for i in all_issues if i.severity == "error")
    warns = sum(1 for i in all_issues if i.severity == "warn")
    infos = sum(1 for i in all_issues if i.severity == "info")
    total = len(all_issues)

    error_weight = min(errors, 10)
    warn_weight = min(warns, 25)
    score = max(0, 100 - error_weight * 10 - warn_weight * 2)

    return Report(
        score=score,
        total=total,
        errors=errors,
        warns=warns,
        infos=infos,
        issues=all_issues,
    )

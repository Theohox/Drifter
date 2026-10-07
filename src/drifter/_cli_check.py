"""CLI handlers for `drifter check` and `drifter session-report`."""

from __future__ import annotations

import argparse

from drifter._cli_common import print_banner, print_rule
from drifter.checks._base import Check, Issue
from drifter.checks.behavioral import (
    DriftCheckAfterWriteCheck,
    NoRushCheck,
    ReadBeforeWriteCheck,
    TestAfterWriteCheck,
    is_drift_check,
    is_test_run,
)
from drifter.config import Config
from drifter.drift_guard import run_checks
from drifter.reporters.console import ConsoleReporter
from drifter.reporters.github_actions import GitHubActionsReporter
from drifter.reporters.json_reporter import JsonReporter
from drifter.session_logger import SessionLogger


def cmd_check(args: argparse.Namespace) -> int:
    config = Config.load(root=args.root)
    report = run_checks(root=args.root, config=config)

    if args.score:
        print(
            f"DRIFT: {report.total} issues | {report.errors} errors | {report.warns} warns | SCORE: {report.score}%"
        )
        return 1 if report.errors > 0 else 0

    meta = {
        "score": report.score,
        "total": report.total,
        "errors": report.errors,
        "warns": report.warns,
        "infos": report.infos,
        "timestamp": report.timestamp,
    }
    # --json is a deprecated alias for --format json; an explicit --format wins
    fmt = args.format or ("json" if args.json else "console")
    if fmt == "json":
        print(JsonReporter().report(report.issues, meta))
    elif fmt == "github":
        print(GitHubActionsReporter().report(report.issues))
    else:
        print(ConsoleReporter().report(report.issues, meta))
    return 1 if report.errors > 0 else 0


def cmd_session_report(args: argparse.Namespace) -> int:
    """Generate session report card from audit log."""
    config = Config.load(root=args.root)
    checks: list[Check] = [
        ReadBeforeWriteCheck(),
        TestAfterWriteCheck(),
        DriftCheckAfterWriteCheck(),
        NoRushCheck(),
    ]

    all_issues: list[Issue] = []
    for check in checks:
        all_issues.extend(check.run(config.root, config))

    print_banner("SESSION REPORT CARD")

    logger = SessionLogger(root=config.root)
    entries = logger.read_entries()
    reads = [e for e in entries if e.action == "READ"]
    writes = [e for e in entries if e.action == "WRITE"]
    shells = [e for e in entries if e.action == "SHELL"]
    tests = [e for e in entries if is_test_run(e.action, e.target)]
    drift_checks = [e for e in entries if is_drift_check(e.action, e.target)]

    print(f"  Files read: {len(reads)}")
    print(f"  Files written: {len(writes)}")
    print(f"  Shell commands: {len(shells)}")
    print(f"  Test runs: {len(tests)}")
    print(f"  Drift checks: {len(drift_checks)}")

    print(ConsoleReporter().report(all_issues))
    # Exit policy is intentionally strict: this command is a gate, so any
    # issue (including warns) fails the report card.
    if all_issues:
        print("  ✗ SESSION REPORT CARD FAILED. Fix violations before declaring done.")
        print_rule()
        return 1
    print("  ✓ SESSION REPORT CARD PASSED. You may declare done.")
    print_rule()
    return 0

"""CLI handlers for preflight, audit, logging, and capability commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from drifter._cli_common import print_banner, print_rule
from drifter.conductor import Conductor
from drifter.config import Config
from drifter.history_reader import HistoryReader
from drifter.manifest_generator import describe_json, describe_markdown, write_manifest
from drifter.pre_flight import run_pre_flight
from drifter.session_logger import SessionLogger
from drifter.shell_guard import ShellGuard


def cmd_preflight(args: argparse.Namespace) -> int:
    config = Config.load(root=args.root)
    result = run_pre_flight(
        root=args.root, config=config, task=args.task, keyword=args.keyword
    )
    result.print_report()

    # Record the planned task in the session audit log
    if args.task:
        SessionLogger(root=config.root).log("TASK", args.task)

    # Record the drift score in the conductor (also refreshes its timestamp)
    conductor = Conductor(root=args.root, config=config)
    if conductor.exists():
        conductor.append_drift_score(result.drift_score, notes="preflight")

    return 0 if result.passed else 1


def cmd_audit(args: argparse.Namespace) -> int:
    config = Config.load(root=args.root)
    guard = ShellGuard(root=args.root)

    print_banner("SESSION AUDIT")

    # Check if dangerous_patterns.toml exists
    patterns_file = config.root / "dangerous_patterns.toml"
    if not patterns_file.exists():
        print("  ✗ dangerous_patterns.toml not found — cannot audit without rules")
        print_rule()
        return 1

    print("  dangerous_patterns.toml: ✓ Found")

    # Read shell history via HistoryReader
    violations = []
    checked = 0

    if not args.no_history:
        reader: HistoryReader | None
        if config.history_path:
            reader = HistoryReader(Path(config.history_path).expanduser())
        else:
            reader = HistoryReader.auto_detect()

        if reader is not None and reader.path is not None and reader.path.exists():
            recent = reader.read_commands(max_entries=args.window)
            for line in recent:
                line = line.strip()
                if not line:
                    continue
                checked += 1
                classification = guard.classify(line)
                if classification.action in ("block", "approval_required", "warn"):
                    violations.append((line, classification))
            print(f"  History source: {reader.path} ({reader.shell})")
        else:
            print(
                "  No shell history found (set history_path in drifter.toml or ensure $SHELL is set)"
            )

    print(f"  Commands checked: {checked}")

    if violations:
        print(f"\n  ✗ {len(violations)} VIOLATION(S) FOUND:")
        for cmd, classification in violations:
            print(f"    • [{classification.action.upper()}] {cmd}")
            print(f"      → {classification.reason}")
    else:
        print("\n  ✓ No violations detected.")

    print_rule()
    return 1 if violations else 0


def cmd_log(args: argparse.Namespace) -> int:
    """Log an action to the session audit log."""
    config = Config.load(root=args.root)
    logger = SessionLogger(root=config.root)
    logger.log(args.action, args.target)
    return 0


def cmd_log_rotate(args: argparse.Namespace) -> int:
    """Archive the current session log and start a fresh one."""
    config = Config.load(root=args.root)
    logger = SessionLogger(root=config.root)
    archive = logger.rotate_log()
    if archive is None:
        print("No session log to rotate.")
        return 0
    print(f"✓ Session log archived: {archive}")
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    config = Config.load(root=args.root)
    path = write_manifest(root=config.root)
    print(f"✓ Capability manifest written: {path}")
    return 0


def cmd_describe(args: argparse.Namespace) -> int:
    config = Config.load(root=args.root)
    if args.format == "markdown":
        print(describe_markdown(root=config.root))
    else:
        print(describe_json(root=config.root))
    return 0

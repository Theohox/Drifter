"""CLI entry point for Drifter."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from drifter.config import Config
from drifter.conductor import Conductor
from drifter.doc_validator import validate_docs
from drifter.drift_guard import run_checks
from drifter.pre_flight import run_pre_flight
from drifter.session_logger import SessionLogger


def _format_issues_console(issues: list, score: int | None = None) -> None:
    print(f"\n{'='*60}")
    print("  DRIFT GUARD REPORT")
    print(f"{'='*60}")
    if score is not None:
        print(f"  Score: {score}/100")
    print(f"  Issues: {len(issues)}")
    print(f"{'='*60}")

    if issues:
        errors = [i for i in issues if i.severity == "error"]
        warns = [i for i in issues if i.severity == "warn"]
        infos = [i for i in issues if i.severity == "info"]
        if errors:
            print(f"\n  Errors ({len(errors)}):")
            for issue in errors:
                print(f"    ✗ {issue}")
        if warns:
            print(f"\n  Warnings ({len(warns)}):")
            for issue in warns:
                print(f"    • {issue}")
        if infos:
            print(f"\n  Info ({len(infos)}):")
            for issue in infos:
                print(f"    ℹ {issue}")
    else:
        print("\n  ✓ No drift detected. System is clean.")

    print(f"{'='*60}\n")


def cmd_check(args: argparse.Namespace) -> int:
    config = Config.load(root=args.root)
    report = run_checks(root=args.root, config=config)

    if args.score:
        print(f"DRIFT: {report.total} issues | {report.errors} errors | {report.warns} warns | SCORE: {report.score}%")
        return 1 if report.errors > 0 else 0

    if args.json:
        print(json.dumps({
            "score": report.score,
            "total": report.total,
            "errors": report.errors,
            "warns": report.warns,
            "infos": report.infos,
            "issues": [repr(i) for i in report.issues],
            "timestamp": report.timestamp,
        }, indent=2))
        return 1 if report.errors > 0 else 0

    if args.format == "github":
        for issue in report.issues:
            level = "error" if issue.severity == "error" else "warning"
            print(f"::{level} file={issue.file}::{issue.check}: {issue.detail}")
        return 1 if report.errors > 0 else 0

    _format_issues_console(report.issues, report.score)
    return 1 if report.errors > 0 else 0


def cmd_preflight(args: argparse.Namespace) -> int:
    config = Config.load(root=args.root)
    result = run_pre_flight(root=args.root, config=config, task=args.task, keyword=args.keyword)
    result.print_report()

    # Auto-update conductor timestamp after preflight
    try:
        conductor = Conductor(root=args.root, config=config)
        if conductor.exists():
            conductor._touch_timestamp()
    except Exception:
        pass

    return 0 if result.passed else 1


def cmd_conductor(args: argparse.Namespace) -> int:
    config = Config.load(root=args.root)
    conductor = Conductor(root=args.root, config=config)

    if args.conductor_command == "init":
        path = conductor.init(force=args.force)
        print(f"Conductor initialized at {path}")
        return 0

    if args.conductor_command == "show":
        info = conductor.show()
        if "error" in info:
            print(f"Error: {info['error']}")
            return 1
        print(f"\n{'='*60}")
        print("  CONDUCTOR")
        print(f"{'='*60}")
        print(f"  Phase: {info['phase']}")
        if info.get("active_task"):
            task = info["active_task"]
            print(f"\n  Active Task:")
            print(f"    ID:       {task['id']}")
            print(f"    Name:     {task['name']}")
            print(f"    Status:   {task['status']}")
            print(f"    Evidence: {task['evidence']}")
        print(f"{'='*60}\n")
        return 0

    if args.conductor_command == "done":
        if not args.task_id:
            print("Error: --task-id required")
            return 1
        success = conductor.mark_done(args.task_id, args.evidence or "")
        if success:
            print(f"Task {args.task_id} marked as done.")
            return 0
        print("Error: Could not mark task as done. Is the conductor format correct?")
        return 1

    if args.conductor_command == "block":
        if not args.task_id or not args.reason:
            print("Error: --task-id and --reason required")
            return 1
        success = conductor.block_task(args.task_id, args.reason)
        if success:
            print(f"Task {args.task_id} added to blocked tasks.")
            return 0
        print("Error: Could not block task. Is the conductor format correct?")
        return 1

    if args.conductor_command == "next":
        info = conductor.next_task()
        print(info.get("message", ""))
        if "hint" in info:
            print(f"Hint: {info['hint']}")
        return 0

    print(f"Unknown conductor command: {args.conductor_command}")
    return 1


def cmd_validate(args: argparse.Namespace) -> int:
    config = Config.load(root=args.root)
    report = validate_docs(root=args.root, config=config)

    print(f"\n{'='*60}")
    print("  DOCUMENT VALIDATION")
    print(f"{'='*60}")
    print(f"  Issues: {report.total} ({report.errors} errors, {report.warns} warnings)")
    print(f"{'='*60}")

    if report.issues:
        print("\n  Issues found:")
        for issue in report.issues:
            print(f"    • {issue}")
    else:
        print("\n  ✓ All documents valid.")

    print(f"{'='*60}\n")
    return 1 if report.errors > 0 else 0


def cmd_audit(args: argparse.Namespace) -> int:
    from drifter.shell_guard import ShellGuard

    config = Config.load(root=args.root)
    guard = ShellGuard(root=args.root)

    print(f"\n{'='*60}")
    print("  SESSION AUDIT")
    print(f"{'='*60}")

    # Check if dangerous_patterns.toml exists
    patterns_file = config.root / "dangerous_patterns.toml"
    if not patterns_file.exists():
        print("  ✗ dangerous_patterns.toml not found — cannot audit without rules")
        print(f"{'='*60}\n")
        return 1

    print("  dangerous_patterns.toml: ✓ Found")

    # Try to read bash history for audit
    history_path = Path.home() / ".bash_history"
    violations = []
    checked = 0

    if history_path.exists() and not args.no_history:
        lines = history_path.read_text(encoding="utf-8").strip().split("\n")
        # Check last N commands (default 100)
        window = args.window or 100
        recent_lines = lines[-window:] if len(lines) > window else lines

        for line in recent_lines:
            line = line.strip()
            if not line:
                continue
            checked += 1
            classification = guard.classify(line)
            if classification.action in ("block", "approval_required", "warn"):
                violations.append((line, classification))

    print(f"  Commands checked: {checked}")

    if violations:
        print(f"\n  ✗ {len(violations)} VIOLATION(S) FOUND:")
        for cmd, classification in violations:
            print(f"    • [{classification.action.upper()}] {cmd}")
            print(f"      → {classification.reason}")
    else:
        print("\n  ✓ No violations detected.")

    print(f"{'='*60}\n")
    return 1 if violations else 0


def _doc_stub(title: str, doc_type: str, phase: str, now: str) -> str:
    """Generate a minimal doc stub with correct frontmatter."""
    return f"""---
title: {title}
type: {doc_type}
status: active
phase: {phase}
created: '{now}'
updated: '{now}'
---

# {title}

> **TODO**: Fill in this document. This is a stub generated by `drifter init --full`.

*(Add your content here.)*
"""


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.root or ".").resolve()
    root.mkdir(parents=True, exist_ok=True)

    # Create docs directory
    docs_dir = root / "docs"
    digests_dir = docs_dir / "digests"
    digests_dir.mkdir(parents=True, exist_ok=True)
    archive_dir = docs_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Copy templates
    # Try src/ layout first (project root / templates), then fallback
    template_dir = Path(__file__).parent.parent.parent / "templates"
    if not template_dir.exists():
        template_dir = Path(__file__).parent.parent / "templates"
    files_to_create: dict[Path, Path | None] = {
        root / "AGENTS.md": template_dir / "AGENTS.md.tmpl",
        root / "dangerous_patterns.toml": template_dir / "dangerous_patterns.toml.tmpl",
        docs_dir / "session-protocol.md": template_dir / "session-protocol.md.tmpl",
        docs_dir / "project-conductor.md": template_dir / "project-conductor.md.tmpl",
        digests_dir / "index.md": template_dir / "digest-index.md.tmpl",
        archive_dir / "README.md": template_dir / "archive-readme.md.tmpl",
        root / "drifter.toml": template_dir / "drifter.toml.tmpl",
    }

    # Core doc stubs — always created so AGENTS.md canonical document map has real targets
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core_doc_stubs: dict[Path, str] = {
        docs_dir / "methodology.md": _doc_stub("Methodology", "constitution", "0", now),
        docs_dir / "architecture.md": _doc_stub("Architecture", "snapshot", "0", now),
        docs_dir / "adoption-guide.md": _doc_stub("Adoption Guide", "guide", "0", now),
        docs_dir / "rules-reference.md": _doc_stub("Rules Reference", "reference", "0", now),
    }

    created = []
    skipped = []
    project_name = root.name or "my-project"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for dest, src in files_to_create.items():
        if dest.exists() and not args.force:
            skipped.append(str(dest.relative_to(root)))
            continue
        if src is not None and src.exists():
            content = src.read_text(encoding="utf-8")
            content = content.replace("{{PROJECT_NAME}}", project_name)
            content = content.replace("{{NOW}}", now)
        else:
            content = f"# {dest.name}\n\n(Template not found. Please create this file manually.)\n"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        created.append(str(dest.relative_to(root)))

    # Write core doc stubs
    for dest, content in core_doc_stubs.items():
        if dest.exists() and not args.force:
            skipped.append(str(dest.relative_to(root)))
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        created.append(str(dest.relative_to(root)))

    print(f"\n{'='*60}")
    print("  DRIFTER INIT")
    print(f"{'='*60}")
    print(f"  Root: {root}")
    mode = "full" if args.full else "minimal"
    print(f"  Mode: {mode} ({len(created)} created, {len(skipped)} skipped)")
    if created:
        print(f"\n  Created:")
        for f in created:
            print(f"    ✓ {f}")
    if skipped:
        print(f"\n  Skipped (already exist, use --force to overwrite):")
        for f in skipped:
            print(f"    • {f}")
    print(f"\n  Next steps:")
    print(f"    1. Edit AGENTS.md with your project specifics")
    print(f"    2. Edit docs/session-protocol.md with your rules")
    print(f"    3. Edit docs/project-conductor.md with your active task")
    print(f"    4. Run 'drifter check' to verify")
    if skipped:
        print(f"\n  To refresh existing files with latest templates:")
        print(f"    drifter init --force")
    print(f"{'='*60}\n")
    return 0




def cmd_log(args: argparse.Namespace) -> int:
    """Log an action to the session audit log."""
    config = Config.load(root=args.root)
    logger = SessionLogger(root=config.root)
    logger.log(args.action, args.target)
    return 0


def cmd_session_report(args: argparse.Namespace) -> int:
    """Generate session report card from audit log."""
    from drifter.checks.behavioral import (
        ReadBeforeWriteCheck,
        TestAfterWriteCheck,
        DriftCheckAfterWriteCheck,
        NoRushCheck,
    )
    from drifter.config import Config

    config = Config.load(root=args.root)
    checks = [
        ReadBeforeWriteCheck(),
        TestAfterWriteCheck(),
        DriftCheckAfterWriteCheck(),
        NoRushCheck(),
    ]

    all_issues: list = []
    for check in checks:
        all_issues.extend(check.run(config.root, config))

    print(f"\n{'='*60}")
    print("  SESSION REPORT CARD")
    print(f"{'='*60}")

    logger = SessionLogger(root=config.root)
    entries = logger.read_entries()
    reads = [e for e in entries if e.action == "READ"]
    writes = [e for e in entries if e.action == "WRITE"]
    shells = [e for e in entries if e.action == "SHELL"]
    tests = [e for e in entries if "pytest" in e.target or "test" in e.target.lower()]
    drift_checks = [e for e in entries if "drifter check" in e.target]

    print(f"  Files read: {len(reads)}")
    print(f"  Files written: {len(writes)}")
    print(f"  Shell commands: {len(shells)}")
    print(f"  Test runs: {len(tests)}")
    print(f"  Drift checks: {len(drift_checks)}")

    if all_issues:
        errors = [i for i in all_issues if i.severity == "error"]
        warns = [i for i in all_issues if i.severity == "warn"]
        if errors:
            print(f"\n  Errors ({len(errors)}):")
            for issue in errors:
                print(f"    ✗ {issue}")
        if warns:
            print(f"\n  Warnings ({len(warns)}):")
            for issue in warns:
                print(f"    • {issue}")
        print(f"\n  ✗ SESSION REPORT CARD FAILED. Fix violations before declaring done.")
        print(f"{'='*60}\n")
        return 1
    else:
        print(f"\n  ✓ SESSION REPORT CARD PASSED. You may declare done.")
        print(f"{'='*60}\n")
        return 0

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="drifter",
        description="Universal drift guard for AI agents",
    )
    parser.add_argument("--root", type=Path, default=None, help="Project root directory")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # check
    check_parser = subparsers.add_parser("check", help="Run drift guard")
    check_parser.add_argument("--score", action="store_true", help="Print one-line score only")
    check_parser.add_argument("--json", action="store_true", help="Output JSON report")
    check_parser.add_argument("--format", choices=["console", "github"], default="console", help="Output format")
    check_parser.set_defaults(func=cmd_check)

    # preflight
    preflight_parser = subparsers.add_parser("preflight", help="Run pre-flight checklist")
    preflight_parser.add_argument("--task", default=None, help="Description of planned task")
    preflight_parser.add_argument("--keyword", default=None, help="Keyword to grep for in src/ (pre-flight step 6)")
    preflight_parser.set_defaults(func=cmd_preflight)

    # conductor
    conductor_parser = subparsers.add_parser("conductor", help="Manage project conductor")
    conductor_sub = conductor_parser.add_subparsers(dest="conductor_command", required=True)

    conductor_init = conductor_sub.add_parser("init", help="Initialize conductor")
    conductor_init.add_argument("--force", action="store_true", help="Overwrite existing")
    conductor_init.set_defaults(func=cmd_conductor)

    conductor_show = conductor_sub.add_parser("show", help="Show active task")
    conductor_show.set_defaults(func=cmd_conductor)

    conductor_done = conductor_sub.add_parser("done", help="Mark task as done")
    conductor_done.add_argument("--task-id", required=True, help="Task ID")
    conductor_done.add_argument("--evidence", default="", help="Evidence of completion")
    conductor_done.set_defaults(func=cmd_conductor)

    conductor_block = conductor_sub.add_parser("block", help="Block a task")
    conductor_block.add_argument("--task-id", required=True, help="Task ID")
    conductor_block.add_argument("--reason", required=True, help="Reason for blocking")
    conductor_block.set_defaults(func=cmd_conductor)

    conductor_next = conductor_sub.add_parser("next", help="Show next ready task")
    conductor_next.set_defaults(func=cmd_conductor)

    conductor_parser.set_defaults(func=cmd_conductor)

    # validate
    validate_parser = subparsers.add_parser("validate", help="Validate document types")
    validate_parser.set_defaults(func=cmd_validate)

    # audit
    audit_parser = subparsers.add_parser("audit", help="Audit session for dangerous command violations")
    audit_parser.add_argument("--window", type=int, default=100, help="Number of recent history commands to check")
    audit_parser.add_argument("--no-history", action="store_true", help="Skip bash history check")
    audit_parser.set_defaults(func=cmd_audit)

    # init
    init_parser = subparsers.add_parser("init", help="Initialize Drifter in a project")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    init_parser.add_argument("--full", action="store_true", help="Also create optional doc stubs (methodology, architecture, adoption-guide, rules-reference)")
    init_parser.set_defaults(func=cmd_init)

    # log
    log_parser = subparsers.add_parser("log", help="Log an action to the session audit log")
    log_parser.add_argument("action", choices=["READ", "WRITE", "SHELL", "CHECK"], help="Action type")
    log_parser.add_argument("target", help="Target file or command")
    log_parser.set_defaults(func=cmd_log)

    # session-report
    report_parser = subparsers.add_parser("session-report", help="Generate session report card")
    report_parser.set_defaults(func=cmd_session_report)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

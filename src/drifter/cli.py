"""CLI entry point for Drifter.

Parser construction and dispatch live here; command handlers live in the
`_cli_*` modules (`_cli_check`, `_cli_conductor`, `_cli_init`, `_cli_admin`,
`_hook_commands`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from drifter._cli_admin import (
    cmd_audit,
    cmd_describe,
    cmd_log,
    cmd_log_rotate,
    cmd_manifest,
    cmd_preflight,
)
from drifter._cli_check import cmd_check, cmd_session_report
from drifter._cli_conductor import cmd_conductor
from drifter._cli_init import cmd_init, cmd_validate
from drifter._commit_commands import cmd_approve, cmd_commit_msg
from drifter._hook_commands import cmd_install_hook, cmd_uninstall_hook


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="drifter",
        description="Universal drift guard for AI agents",
    )
    parser.add_argument(
        "--root", type=Path, default=None, help="Project root directory"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # check
    check_parser = subparsers.add_parser("check", help="Run drift guard")
    check_parser.add_argument(
        "--score", action="store_true", help="Print one-line score only"
    )
    check_parser.add_argument(
        "--json",
        action="store_true",
        help="Deprecated alias for --format json",
    )
    check_parser.add_argument(
        "--format",
        choices=["console", "json", "github"],
        default=None,
        help="Output format (default: console)",
    )
    check_parser.set_defaults(func=cmd_check)

    # preflight
    preflight_parser = subparsers.add_parser(
        "preflight", help="Run pre-flight checklist"
    )
    preflight_parser.add_argument(
        "--task", default=None, help="Description of planned task"
    )
    preflight_parser.add_argument(
        "--keyword",
        default=None,
        help="Keyword to grep for in src/ (pre-flight step 6)",
    )
    preflight_parser.set_defaults(func=cmd_preflight)

    # conductor
    conductor_parser = subparsers.add_parser(
        "conductor", help="Manage project conductor"
    )
    conductor_sub = conductor_parser.add_subparsers(
        dest="conductor_command", required=True
    )

    conductor_init = conductor_sub.add_parser("init", help="Initialize conductor")
    conductor_init.add_argument(
        "--force", action="store_true", help="Overwrite existing"
    )
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

    # validate
    validate_parser = subparsers.add_parser("validate", help="Validate document types")
    validate_parser.set_defaults(func=cmd_validate)

    # audit
    audit_parser = subparsers.add_parser(
        "audit", help="Audit session for dangerous command violations"
    )
    audit_parser.add_argument(
        "--window",
        type=int,
        default=100,
        help="Number of recent history commands to check",
    )
    audit_parser.add_argument(
        "--no-history",
        action="store_true",
        help="Skip shell history check (bash/zsh/fish)",
    )
    audit_parser.set_defaults(func=cmd_audit)

    # init
    init_parser = subparsers.add_parser("init", help="Initialize Drifter in a project")
    init_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing files"
    )
    init_parser.add_argument(
        "--full",
        action="store_true",
        help="Also create optional doc stubs (methodology, architecture, adoption-guide, rules-reference)",
    )
    init_parser.set_defaults(func=cmd_init)

    # log
    log_parser = subparsers.add_parser(
        "log", help="Log an action to the session audit log"
    )
    log_parser.add_argument(
        "action", choices=["READ", "WRITE", "SHELL", "CHECK"], help="Action type"
    )
    log_parser.add_argument("target", help="Target file or command")
    log_parser.set_defaults(func=cmd_log)

    # log-rotate
    log_rotate_parser = subparsers.add_parser(
        "log-rotate", help="Archive the session log and start a fresh one"
    )
    log_rotate_parser.set_defaults(func=cmd_log_rotate)

    # session-report
    report_parser = subparsers.add_parser(
        "session-report", help="Generate session report card"
    )
    report_parser.set_defaults(func=cmd_session_report)

    # install-hook
    install_hook_parser = subparsers.add_parser(
        "install-hook", help="Install git pre-commit hook"
    )
    install_hook_parser.add_argument(
        "--approval",
        action="store_true",
        help="Also require human approval (`drifter approve`) before each commit",
    )
    install_hook_parser.set_defaults(func=cmd_install_hook)

    # uninstall-hook
    uninstall_hook_parser = subparsers.add_parser(
        "uninstall-hook", help="Uninstall git pre-commit hook"
    )
    uninstall_hook_parser.set_defaults(func=cmd_uninstall_hook)

    # approve
    approve_parser = subparsers.add_parser(
        "approve", help="Arm one-time commit approval (human-only)"
    )
    approve_parser.set_defaults(func=cmd_approve)

    # commit-msg
    commit_msg_parser = subparsers.add_parser(
        "commit-msg", help="Draft a commit message from staged changes"
    )
    commit_msg_parser.set_defaults(func=cmd_commit_msg)

    # manifest
    manifest_parser = subparsers.add_parser(
        "manifest", help="Generate capability manifest"
    )
    manifest_parser.set_defaults(func=cmd_manifest)

    # describe
    describe_parser = subparsers.add_parser(
        "describe", help="Describe project capabilities for LLMs"
    )
    describe_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format",
    )
    describe_parser.set_defaults(func=cmd_describe)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

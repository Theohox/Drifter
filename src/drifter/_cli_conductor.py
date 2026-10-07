"""CLI handlers for `drifter conductor`."""

from __future__ import annotations

import argparse

from drifter._cli_common import print_banner, print_rule
from drifter.conductor import Conductor
from drifter.config import Config


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
        print_banner("CONDUCTOR")
        print(f"  Phase: {info['phase']}")
        if info.get("active_task"):
            task = info["active_task"]
            print("\n  Active Task:")
            print(f"    ID:       {task['id']}")
            print(f"    Name:     {task['name']}")
            print(f"    Status:   {task['status']}")
            print(f"    Evidence: {task['evidence']}")
        print_rule()
        return 0

    if args.conductor_command == "done":
        success = conductor.mark_done(args.task_id, args.evidence or "")
        if success:
            print(f"Task {args.task_id} marked as done.")
            return 0
        print("Error: Could not mark task as done. Is the conductor format correct?")
        return 1

    if args.conductor_command == "block":
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

    # Unreachable via the CLI: argparse enforces a valid subcommand
    raise ValueError(f"Unknown conductor command: {args.conductor_command}")

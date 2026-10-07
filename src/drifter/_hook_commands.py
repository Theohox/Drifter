"""Git pre-commit hook install/uninstall helpers."""

from __future__ import annotations

import argparse
from pathlib import Path

_PRE_COMMIT_HOOK = """#!/bin/sh
# Drifter pre-commit hook — auto-installed by `drifter install-hook`
# Runs drift guard before every commit. Blocks commit on error-level drift.

echo "Running Drifter pre-commit check..."

# Resolution order: repo-local venv, drifter in PATH, python -m fallbacks.
# A human committing from a bare shell has no venv activated — find the
# project's own .venv first so the check is not silently skipped.
if [ -x ".venv/bin/drifter" ]; then
    .venv/bin/drifter check
elif command -v drifter >/dev/null 2>&1; then
    drifter check
elif [ -f ".venv/bin/python" ]; then
    .venv/bin/python -m drifter check
elif command -v python3 >/dev/null 2>&1; then
    python3 -m drifter check
elif command -v python >/dev/null 2>&1; then
    python -m drifter check
else
    echo "Warning: drifter not found (no .venv, not on PATH). Skipping drift check."
    exit 0
fi

if [ $? -ne 0 ]; then
    echo ""
    echo "✗ Drifter check failed. Fix drift before committing."
    echo "   Run 'drifter check' to see issues."
    exit 1
fi

echo "✓ Drifter check passed. Proceeding with commit."
"""

_APPROVAL_GATE = """
# --- Human-approval gate (`drifter install-hook --approval`) ---
# Blocks commits until the human arms a one-time approval.
if [ ! -f ".git/approved" ]; then
    echo ""
    echo "✗ Commit blocked: no human approval."
    echo "   Run:  drifter approve"
    echo "   Then: re-run your git commit."
    echo ""
    exit 1
fi
rm ".git/approved"  # consume — one-time use
"""


def _render_hook(approval: bool) -> str:
    if not approval:
        return _PRE_COMMIT_HOOK
    # Approval gate first, then the drift check.
    body = _PRE_COMMIT_HOOK.replace(
        'echo "Running Drifter pre-commit check..."',
        'echo "Running Drifter pre-commit check..."\n' + _APPROVAL_GATE,
    )
    return body.replace(
        "# Runs drift guard before every commit. Blocks commit on error-level drift.",
        "# Runs drift guard before every commit. Blocks commit on error-level drift.\n"
        "# Also requires `drifter approve` (one-time human approval) per commit.",
    )


def cmd_install_hook(args: argparse.Namespace) -> int:
    """Install the Drifter pre-commit hook."""
    root = args.root or Path(".")
    git_dir = root / ".git"
    if not git_dir.exists():
        print(f"✗ Not a git repository: {root}")
        return 1

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_path = hooks_dir / "pre-commit"
    if hook_path.exists():
        print(f"⚠ Pre-commit hook already exists: {hook_path}")
        print("  Run 'drifter uninstall-hook' first, or manually back it up.")
        return 1

    hook_path.write_text(
        _render_hook(bool(getattr(args, "approval", False))), encoding="utf-8"
    )
    hook_path.chmod(0o755)

    print(f"✓ Pre-commit hook installed: {hook_path}")
    print("  It will run 'drifter check' before every commit.")
    if getattr(args, "approval", False):
        print("  Commits also require one-time human approval: `drifter approve`.")
    return 0


def cmd_uninstall_hook(args: argparse.Namespace) -> int:
    """Uninstall the Drifter pre-commit hook."""
    root = args.root or Path(".")
    hook_path = root / ".git" / "hooks" / "pre-commit"

    if not hook_path.exists():
        print(f"⚠ No pre-commit hook found: {hook_path}")
        return 0

    content = hook_path.read_text(encoding="utf-8")
    if "Drifter pre-commit hook" not in content:
        print(f"⚠ Pre-commit hook exists but was not installed by Drifter: {hook_path}")
        print("  Not removing it to avoid data loss.")
        return 1

    hook_path.unlink()
    print(f"✓ Pre-commit hook removed: {hook_path}")
    return 0

"""Shell Guard — Command classifier based on dangerous_patterns.toml.

Reads the repo root dangerous_patterns.toml and classifies shell commands
as block / warn / allow / approval_required.

This is agent-agnostic: any AI agent can import and use it.
"""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

if sys.version_info < (3, 11):
    import tomli as tomllib


ClassificationAction = Literal["allow", "block", "warn", "approval_required"]


@dataclass(frozen=True)
class Classification:
    action: ClassificationAction
    reason: str
    matched_pattern: str | None = None


class ShellGuard:
    """Classifies shell commands against dangerous_patterns.toml."""

    def __init__(self, root: Path | None = None):
        self.root = (root or Path(".")).resolve()
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> dict:
        patterns_file = self.root / "dangerous_patterns.toml"
        if not patterns_file.exists():
            return {}
        with patterns_file.open("rb") as f:
            return tomllib.load(f)

    def classify(self, command: str) -> Classification:
        """Classify a shell command.

        Returns:
            Classification with action and reason.
        """
        cmd_lower = command.lower().strip()

        # Check git rules
        git = self.patterns.get("git", {})

        for pattern in git.get("always_block", []):
            if pattern.lower() in cmd_lower:
                return Classification(
                    action="block",
                    reason=f"'{pattern}' is in git.always_block — never run this command",
                    matched_pattern=pattern,
                )

        for pattern in git.get("approval_required", []):
            if pattern.lower() in cmd_lower:
                return Classification(
                    action="approval_required",
                    reason=f"'{pattern}' requires explicit human approval",
                    matched_pattern=pattern,
                )

        for pattern in git.get("allowed", []):
            if pattern.lower() in cmd_lower:
                return Classification(
                    action="allow",
                    reason=f"'{pattern}' is in git.allowed",
                    matched_pattern=pattern,
                )

        # Check shell rules
        shell = self.patterns.get("shell", {})

        for pattern in shell.get("blocked", []):
            if pattern.lower() in cmd_lower:
                return Classification(
                    action="block",
                    reason=f"'{pattern}' is in shell.blocked — dangerous pattern",
                    matched_pattern=pattern,
                )

        for pattern in shell.get("confirm_required", []):
            if pattern.lower() in cmd_lower:
                return Classification(
                    action="warn",
                    reason=f"'{pattern}' is in shell.confirm_required — confirm with human",
                    matched_pattern=pattern,
                )

        # Check filesystem rules
        fs = self.patterns.get("filesystem", {})

        for system_dir in fs.get("system_dirs", []):
            if system_dir.lower() in cmd_lower:
                return Classification(
                    action="block",
                    reason=f"'{system_dir}' is in filesystem.system_dirs — never touch system directories",
                    matched_pattern=system_dir,
                )

        for sensitive in fs.get("sensitive_patterns", []):
            # Convert glob-like pattern to a simple substring check
            sensitive_lower = sensitive.lower().replace("*", "")
            if sensitive_lower in cmd_lower:
                return Classification(
                    action="approval_required",
                    reason=f"'{sensitive}' is in filesystem.sensitive_patterns — requires explicit approval",
                    matched_pattern=sensitive,
                )

        return Classification(
            action="allow",
            reason="No dangerous patterns matched",
        )

    def check(self, command: str) -> str:
        """Check a command and return a human-readable result."""
        classification = self.classify(command)
        if classification.action == "block":
            return f"BLOCKED: {classification.reason}"
        if classification.action == "approval_required":
            return f"APPROVAL REQUIRED: {classification.reason}"
        if classification.action == "warn":
            return f"WARNING: {classification.reason}"
        return f"ALLOWED: {classification.reason}"

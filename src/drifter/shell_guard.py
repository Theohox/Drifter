"""Shell Guard — Command classifier based on dangerous_patterns.toml.

Reads the repo root dangerous_patterns.toml and classifies shell commands
as block / warn / allow / approval_required.

Uses shlex tokenization + regex word boundaries for accurate matching.
"""

from __future__ import annotations

import re
import shlex
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

if sys.version_info >= (3, 11):
    import tomllib
else:
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

    @staticmethod
    def _tokenize(command: str) -> list[str] | None:
        """Tokenize a shell command with shlex."""
        try:
            return shlex.split(command)
        except ValueError:
            return None

    @staticmethod
    def _matches(normalized: str, pattern: str) -> bool:
        """Check if pattern matches normalized command with word boundaries.

        Uses regex so that e.g. "git c-o-m-m-i-t" matches "git c-o-m-m-i-t -m x"
        but does NOT match "git c-o-m-m-i-t-msg".
        """
        pattern_lower = pattern.lower()
        escaped = re.escape(pattern_lower)
        # Match at start, after whitespace, before end, or before whitespace
        regex = re.compile(rf"(?:^|\s){escaped}(?:\s|$)")
        return bool(regex.search(normalized))

    def classify(self, command: str) -> Classification:
        """Classify a shell command.

        Returns:
            Classification with action and reason.
        """
        tokens = self._tokenize(command)
        if tokens is None:
            return Classification(
                action="block",
                reason="Unparseable shell syntax",
                matched_pattern=None,
            )

        normalized = " ".join(tokens).lower()

        # Check git rules
        git = self.patterns.get("git", {})

        for pattern in git.get("always_block", []):
            if self._matches(normalized, pattern):
                return Classification(
                    action="block",
                    reason=f"'{pattern}' is in git.always_block — never run this command",
                    matched_pattern=pattern,
                )

        for pattern in git.get("approval_required", []):
            if self._matches(normalized, pattern):
                return Classification(
                    action="approval_required",
                    reason=f"'{pattern}' requires explicit human approval",
                    matched_pattern=pattern,
                )

        for pattern in git.get("allowed", []):
            if self._matches(normalized, pattern):
                return Classification(
                    action="allow",
                    reason=f"'{pattern}' is in git.allowed",
                    matched_pattern=pattern,
                )

        # Check shell rules
        shell = self.patterns.get("shell", {})

        for pattern in shell.get("blocked", []):
            if self._matches(normalized, pattern):
                return Classification(
                    action="block",
                    reason=f"'{pattern}' is in shell.blocked — dangerous pattern",
                    matched_pattern=pattern,
                )

        for pattern in shell.get("confirm_required", []):
            if self._matches(normalized, pattern):
                return Classification(
                    action="warn",
                    reason=f"'{pattern}' is in shell.confirm_required — confirm with human",
                    matched_pattern=pattern,
                )

        # Check filesystem rules (intentional substring matching for paths)
        fs = self.patterns.get("filesystem", {})

        for system_dir in fs.get("system_dirs", []):
            if system_dir.lower() in normalized:
                return Classification(
                    action="block",
                    reason=f"'{system_dir}' is in filesystem.system_dirs — never touch system directories",
                    matched_pattern=system_dir,
                )

        for sensitive in fs.get("sensitive_patterns", []):
            # Convert glob-like pattern to a simple substring check
            sensitive_lower = sensitive.lower().replace("*", "")
            if sensitive_lower in normalized:
                return Classification(
                    action="approval_required",
                    reason=f"'{sensitive}' is in filesystem.sensitive_patterns — requires explicit approval",
                    matched_pattern=sensitive,
                )

        return Classification(
            action="allow",
            reason="No dangerous patterns matched",
        )

    def enforce(self, command: str) -> Classification:
        """Enforce dangerous_patterns against a command.

        Raises DangerousCommandError on block.
        Raises ApprovalRequiredError on approval_required.
        Returns Classification on allow or warn (warn logs a warning).
        """
        from drifter.errors import ApprovalRequiredError, DangerousCommandError

        classification = self.classify(command)
        if classification.action == "block":
            raise DangerousCommandError(
                command=command,
                pattern=classification.matched_pattern,
                reason=classification.reason,
                classification=classification,
            )
        if classification.action == "approval_required":
            raise ApprovalRequiredError(
                command=command,
                pattern=classification.matched_pattern,
                reason=classification.reason,
                classification=classification,
            )
        if classification.action == "warn":
            warnings.warn(
                f"DANGEROUS COMMAND WARNING: {classification.reason} (command: '{command}')",
                stacklevel=2,
            )
        return classification

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

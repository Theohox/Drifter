"""Shell Guard — Command classifier based on dangerous_patterns.toml.

Reads the repo root dangerous_patterns.toml and classifies shell commands
as block / warn / allow / approval_required.

Compound commands (&&, ||, ;, |) are split into segments; every segment is
classified and the strictest verdict wins (block > approval_required > warn >
allow), so an allowed prefix like `git status` cannot smuggle a blocked
command past the allow-list. Pipelines whose source is a downloader
(curl/wget) and whose sink is a shell (sh/bash) match the pipe-to-shell
patterns in shell.blocked even when the commands carry real-world flags.

Fail-closed: if dangerous_patterns.toml is missing, unparseable, or contains
no git/shell/filesystem rule sections (e.g. an empty or truncated file),
every command classifies as block.

Uses shlex tokenization + regex word boundaries for accurate matching.
"""

from __future__ import annotations

import re
import shlex
import warnings
from pathlib import Path

from drifter._toml_utils import safe_load_toml
from drifter._types import Classification
from drifter.errors import ApprovalRequiredError, DangerousCommandError


_ACTION_SEVERITY = {"allow": 0, "warn": 1, "approval_required": 2, "block": 3}

_RULE_SECTIONS = ("git", "shell", "filesystem")


class ShellGuard:
    """Classifies shell commands against dangerous_patterns.toml."""

    def __init__(self, root: Path | None = None):
        self.root = (root or Path(".")).resolve()
        self.patterns, self._load_error = self._load_patterns()

    def _load_patterns(self) -> tuple[dict, str | None]:
        patterns_file = self.root / "dangerous_patterns.toml"
        data = safe_load_toml(patterns_file)
        if data is None:
            return {}, (
                "dangerous_patterns.toml missing/corrupt — "
                "enforcement fail-closed, all commands blocked"
            )
        if not any(data.get(section) for section in _RULE_SECTIONS):
            return {}, (
                "dangerous_patterns.toml has no git/shell/filesystem rules "
                "(empty or truncated?) — enforcement fail-closed, "
                "all commands blocked"
            )
        return data, None

    @staticmethod
    def _split_compound(command: str) -> list[tuple[str, str]] | None:
        """Split a command into (segment_text, connector) pairs.

        connector is the operator joining this segment to the previous one:
        "" for the first segment, otherwise one of "&&", "||", ";", "&", "|".
        Quote-aware: operators inside single/double quotes are not split.
        Returns None on unclosed quotes or a dangling escape.
        """
        segments: list[tuple[str, str]] = []
        buf: list[str] = []
        quote: str | None = None
        escaped = False
        connector = ""

        def flush(next_connector: str) -> None:
            nonlocal connector
            text = "".join(buf).strip()
            buf.clear()
            if text:
                segments.append((text, connector))
            connector = next_connector

        i = 0
        n = len(command)
        while i < n:
            ch = command[i]
            if escaped:
                buf.append(ch)
                escaped = False
            elif quote is not None:
                if ch == quote:
                    quote = None
                buf.append(ch)
            elif ch in ("'", '"'):
                quote = ch
                buf.append(ch)
            elif ch == "\\":
                escaped = True
                buf.append(ch)
            elif ch == ";":
                flush(";")
            elif ch == "&":
                if i + 1 < n and command[i + 1] == "&":
                    flush("&&")
                    i += 1
                else:
                    flush("&")
            elif ch == "|":
                if i + 1 < n and command[i + 1] == "|":
                    flush("||")
                    i += 1
                else:
                    flush("|")
            else:
                buf.append(ch)
            i += 1

        if quote is not None or escaped:
            return None
        flush("")
        return segments

    @staticmethod
    def _tokenize(segment: str) -> list[str] | None:
        """Tokenize a shell command segment with shlex."""
        try:
            return shlex.split(segment)
        except ValueError:
            return None

    @staticmethod
    def _matches(normalized: str, pattern: str) -> bool:
        """Check if pattern matches normalized command with word boundaries.

        Uses regex so that e.g. "git c-o-m-m-i-t" matches "git c-o-m-m-i-t -m x"
        but does NOT match "git c-o-m-m-i-t-msg".

        Patterns ending in a non-word character (e.g. "dd if=", "rm -rf /")
        are prefix patterns: no trailing boundary is required, so
        "dd if=" matches "dd if=/dev/zero".
        """
        pattern_lower = pattern.lower()
        escaped = re.escape(pattern_lower)
        # Match at start or after whitespace
        if pattern_lower[-1].isalnum():
            # Word-boundary at the end: no false positives on longer words
            regex = re.compile(rf"(?:^|\s){escaped}(?:\s|$)")
        else:
            regex = re.compile(rf"(?:^|\s){escaped}")
        return bool(regex.search(normalized))

    def _classify_pipeline(
        self, pipe_segments: list[list[str]]
    ) -> Classification | None:
        """Block downloader-to-shell pipes (e.g. curl ... | sh).

        A pipeline whose sink is a shell and whose source is a downloader is
        matched against the pipe-to-shell patterns in shell.blocked, so
        `curl -fsSL URL | sh` hits the "curl | sh" rule despite the flags.
        """
        if len(pipe_segments) < 2:
            return None
        blocked = [p.lower() for p in self.patterns.get("shell", {}).get("blocked", [])]
        for sink_idx in range(1, len(pipe_segments)):
            sink_tokens = pipe_segments[sink_idx]
            if not sink_tokens:
                continue
            sink = sink_tokens[0]
            for source_tokens in pipe_segments[:sink_idx]:
                if not source_tokens:
                    continue
                candidate = f"{source_tokens[0]} | {sink}"
                if candidate in blocked:
                    return Classification(
                        action="block",
                        reason=(
                            f"'{candidate}' is in shell.blocked — "
                            "pipe-to-shell execution, never run this"
                        ),
                        matched_pattern=candidate,
                    )
        return None

    def _classify_normalized(self, normalized: str) -> Classification:
        """Classify a single normalized command segment."""
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
            if "|" in pattern:
                # Pipe-to-shell patterns are enforced by _classify_pipeline
                continue
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

    def classify(self, command: str) -> Classification:
        """Classify a shell command.

        Compound commands are split on &&, ||, ;, & and | (quote-aware) and
        every segment is classified; the strictest verdict wins.

        Returns:
            Classification with action and reason.
        """
        if self._load_error is not None:
            return Classification(action="block", reason=self._load_error)

        segments = self._split_compound(command)
        if segments is None:
            return Classification(
                action="block",
                reason="Unparseable shell syntax",
                matched_pattern=None,
            )

        best = Classification(action="allow", reason="No dangerous patterns matched")
        pipeline: list[list[str]] = []

        def consider(candidate: Classification | None) -> None:
            nonlocal best
            if candidate is not None and (
                _ACTION_SEVERITY[candidate.action] > _ACTION_SEVERITY[best.action]
            ):
                best = candidate

        for text, connector in segments:
            if connector != "|":
                consider(self._classify_pipeline(pipeline))
                pipeline = []
            tokens = self._tokenize(text)
            if tokens is None:
                return Classification(
                    action="block",
                    reason="Unparseable shell syntax",
                    matched_pattern=None,
                )
            if tokens:
                pipeline.append(tokens)
                consider(self._classify_normalized(" ".join(tokens).lower()))
        consider(self._classify_pipeline(pipeline))

        return best

    def enforce(self, command: str) -> Classification:
        """Enforce dangerous_patterns against a command.

        Raises DangerousCommandError on block.
        Raises ApprovalRequiredError on approval_required.
        Returns Classification on allow or warn (warn logs a warning).
        """
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

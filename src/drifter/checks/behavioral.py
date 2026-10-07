"""Behavioral checks that verify agent session patterns from the audit log."""

from __future__ import annotations

import re
import shlex
import threading
from pathlib import Path

from drifter.checks._base import Issue
from drifter.config import Config
from drifter.session_logger import LogEntry, SessionLogger

# The behavioral checks all read the same session log; parse it once per
# run and share the result. Keyed by (path, mtime) so a log that changed
# mid-run is re-read, and cleared on each new snapshot so stale entries
# from other roots never accumulate.
_log_cache: dict[tuple[str, int], list[LogEntry]] = {}
_log_cache_lock = threading.Lock()


def _load_entries(root: Path) -> list[LogEntry]:
    """Read session log entries, cached per (log path, mtime)."""
    logger = SessionLogger(root=root)
    try:
        mtime = logger.path.stat().st_mtime_ns
    except OSError:
        return []
    key = (str(logger.path), mtime)
    with _log_cache_lock:
        cached = _log_cache.get(key)
        if cached is not None:
            return cached
    entries = logger.read_entries()
    with _log_cache_lock:
        _log_cache.clear()
        _log_cache[key] = entries
    return entries


def _command_segments(target: str) -> list[list[str]]:
    """Split a logged shell command into per-segment token lists."""
    segments: list[list[str]] = []
    for segment in re.split(r"&&|\|\||[;|]", target):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            tokens = segment.split()
        if tokens:
            segments.append(tokens)
    return segments


_PYTHON_HEAD = re.compile(r"(.*/)?python[\d.]*")


def _is_module_run(tokens: list[str], module: str, args: list[str]) -> bool:
    """True for `python -m <module> <args...>` invocations."""
    return (
        bool(_PYTHON_HEAD.fullmatch(tokens[0]))
        and len(tokens) >= 3 + len(args)
        and tokens[1] == "-m"
        and tokens[2] == module
        and tokens[3 : 3 + len(args)] == args
    )


def is_test_run(action: str, target: str) -> bool:
    """True if a log entry represents a test run (SHELL invoking pytest)."""
    if action != "SHELL":
        return False
    for tokens in _command_segments(target):
        if re.fullmatch(r"(.*/)?pytest", tokens[0]):
            return True
        if _is_module_run(tokens, "pytest", []):
            return True
    return False


def is_drift_check(action: str, target: str) -> bool:
    """True if a log entry represents a drift-guard run.

    CHECK-action entries always count; SHELL entries must invoke
    ``drifter check`` as a command (not merely mention it, e.g. in an
    echo). Shared by the behavioral checks and session-report so all
    consumers agree on what a drift check is.
    """
    if action == "CHECK":
        return True
    if action != "SHELL":
        return False
    for tokens in _command_segments(target):
        if re.fullmatch(r"(.*/)?drifter", tokens[0]):
            if len(tokens) > 1 and tokens[1] == "check":
                return True
        elif _is_module_run(tokens, "drifter", ["check"]):
            return True
    return False


class ReadBeforeWriteCheck:
    """Verify every WRITE has a preceding READ on the same file.

    Uses a two-pass approach so that READ entries anywhere in the log
    (including after context compaction) satisfy the check for earlier WRITEs.
    The intent is to verify files were read before modification, not to
    enforce strict chronological ordering in an append-only log.
    """

    name = "read_before_write"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        entries = _load_entries(root)

        # First pass: collect all read targets across the entire log
        read_targets: set[str] = set()
        for entry in entries:
            if entry.action == "READ":
                read_targets.add(entry.target)

        # Second pass: check writes against the full set of reads
        written_without_read: set[str] = set()
        for entry in entries:
            if entry.action == "WRITE":
                if (
                    entry.target not in read_targets
                    and entry.target not in written_without_read
                ):
                    issues.append(
                        Issue(
                            check=self.name,
                            file="session.log",
                            detail=f"WRITE {entry.target} without preceding READ",
                            severity="error",
                        )
                    )
                    written_without_read.add(entry.target)
        return issues


def _find_last_write_index(entries: list[LogEntry]) -> int:
    """Return index of last WRITE entry, or -1 if none."""
    for i in range(len(entries) - 1, -1, -1):
        if entries[i].action == "WRITE":
            return i
    return -1


class TestAfterWriteCheck:
    """Verify a test run happened after the most recent WRITE."""

    name = "test_after_write"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        entries = _load_entries(root)

        last_write_idx = _find_last_write_index(entries)
        if last_write_idx == -1:
            return issues

        for entry in entries[last_write_idx + 1 :]:
            if is_test_run(entry.action, entry.target):
                return issues

        issues.append(
            Issue(
                check=self.name,
                file="session.log",
                detail="Last WRITE not followed by a test run",
                severity="error",
            )
        )
        return issues


class DriftCheckAfterWriteCheck:
    """Verify drifter check was run after the most recent WRITE."""

    name = "drift_check_after_write"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        entries = _load_entries(root)

        last_write_idx = _find_last_write_index(entries)
        if last_write_idx == -1:
            return issues

        for entry in entries[last_write_idx + 1 :]:
            if is_drift_check(entry.action, entry.target):
                return issues

        issues.append(
            Issue(
                check=self.name,
                file="session.log",
                detail="Last WRITE not followed by 'drifter check'",
                severity="error",
            )
        )
        return issues


class NoRushCheck:
    """Verify at least one drift check per 3 WRITEs.

    Warns at ratios above 3:1.
    Errors at ratios above 10:1 (severe rushing).
    """

    name = "no_rush"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        entries = _load_entries(root)

        write_count = 0
        drift_count = 0
        for entry in entries:
            if entry.action == "WRITE":
                write_count += 1
            elif is_drift_check(entry.action, entry.target):
                drift_count += 1

        if write_count > 0 and drift_count == 0:
            issues.append(
                Issue(
                    check=self.name,
                    file="session.log",
                    detail=f"{write_count} WRITEs with zero 'drifter check' runs — session is rushing",
                    severity="error",
                )
            )
        elif write_count > 0:
            ratio = write_count / max(drift_count, 1)
            if ratio > 10:
                issues.append(
                    Issue(
                        check=self.name,
                        file="session.log",
                        detail=f"{write_count} WRITEs vs {drift_count} drift checks (ratio {ratio:.1f}:1) — severe rushing (max 3:1)",
                        severity="error",
                    )
                )
            elif ratio > 3:
                issues.append(
                    Issue(
                        check=self.name,
                        file="session.log",
                        detail=f"{write_count} WRITEs vs {drift_count} drift checks (ratio {ratio:.1f}:1) — max 3:1",
                        severity="warn",
                    )
                )
        return issues

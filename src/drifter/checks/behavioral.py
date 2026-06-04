"""Behavioral checks that verify agent session patterns from the audit log."""

from __future__ import annotations

from pathlib import Path

from drifter.checks._base import Check, Issue
from drifter.config import Config
from drifter.session_logger import SessionLogger


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
        logger = SessionLogger(root=root)
        entries = logger.read_entries()

        # First pass: collect all read targets across the entire log
        read_targets: set[str] = set()
        for entry in entries:
            if entry.action == "READ":
                read_targets.add(entry.target)

        # Second pass: check writes against the full set of reads
        written_without_read: set[str] = set()
        for entry in entries:
            if entry.action == "WRITE":
                if entry.target not in read_targets and entry.target not in written_without_read:
                    issues.append(Issue(
                        check=self.name,
                        file="session.log",
                        detail=f"WRITE {entry.target} without preceding READ",
                        severity="error",
                    ))
                    written_without_read.add(entry.target)
        return issues


def _find_last_write_index(entries: list) -> int:
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
        logger = SessionLogger(root=root)
        entries = logger.read_entries()

        last_write_idx = _find_last_write_index(entries)
        if last_write_idx == -1:
            return issues

        for entry in entries[last_write_idx + 1 :]:
            if entry.action == "SHELL" and ("pytest" in entry.target or "python3 -m pytest" in entry.target):
                return issues

        issues.append(Issue(
            check=self.name,
            file="session.log",
            detail="Last WRITE not followed by a test run",
            severity="error",
        ))
        return issues


class DriftCheckAfterWriteCheck:
    """Verify drifter check was run after the most recent WRITE."""

    name = "drift_check_after_write"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        logger = SessionLogger(root=root)
        entries = logger.read_entries()

        last_write_idx = _find_last_write_index(entries)
        if last_write_idx == -1:
            return issues

        for entry in entries[last_write_idx + 1 :]:
            if entry.action in ("SHELL", "CHECK") and "drifter check" in entry.target:
                return issues

        issues.append(Issue(
            check=self.name,
            file="session.log",
            detail="Last WRITE not followed by 'drifter check'",
            severity="error",
        ))
        return issues


class NoRushCheck:
    """Verify at least one drift check per 3 WRITEs.

    Warns at ratios above 3:1.
    Errors at ratios above 10:1 (severe rushing).
    """

    name = "no_rush"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        logger = SessionLogger(root=root)
        entries = logger.read_entries()

        write_count = 0
        drift_count = 0
        for entry in entries:
            if entry.action == "WRITE":
                write_count += 1
            elif entry.action in ("SHELL", "CHECK") and "drifter check" in entry.target:
                drift_count += 1

        if write_count > 0 and drift_count == 0:
            issues.append(Issue(
                check=self.name,
                file="session.log",
                detail=f"{write_count} WRITEs with zero 'drifter check' runs — session is rushing",
                severity="error",
            ))
        elif write_count > 0:
            ratio = write_count / max(drift_count, 1)
            if ratio > 10:
                issues.append(Issue(
                    check=self.name,
                    file="session.log",
                    detail=f"{write_count} WRITEs vs {drift_count} drift checks (ratio {ratio:.1f}:1) — severe rushing (max 3:1)",
                    severity="error",
                ))
            elif ratio > 3:
                issues.append(Issue(
                    check=self.name,
                    file="session.log",
                    detail=f"{write_count} WRITEs vs {drift_count} drift checks (ratio {ratio:.1f}:1) — max 3:1",
                    severity="warn",
                ))
        return issues

"""Behavioral checks that verify agent session patterns from the audit log."""

from __future__ import annotations

from pathlib import Path

from drifter.checks._base import Check, Issue
from drifter.config import Config
from drifter.session_logger import SessionLogger


class ReadBeforeWriteCheck:
    """Verify every WRITE has a preceding READ on the same file."""

    name = "read_before_write"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        logger = SessionLogger(root=root)
        entries = logger.read_entries()

        read_targets: set[str] = set()
        for entry in entries:
            if entry.action == "READ":
                read_targets.add(entry.target)
            elif entry.action == "WRITE":
                if entry.target not in read_targets:
                    issues.append(Issue(
                        check=self.name,
                        file="session.log",
                        detail=f"WRITE {entry.target} without preceding READ",
                        severity="error",
                    ))
        return issues


class TestAfterWriteCheck:
    """Verify a test run happened after the most recent WRITE."""

    name = "test_after_write"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        logger = SessionLogger(root=root)
        entries = logger.read_entries()

        if not entries:
            return issues

        # Find the last write
        last_write_idx = -1
        for i, entry in enumerate(entries):
            if entry.action == "WRITE":
                last_write_idx = i

        if last_write_idx == -1:
            return issues

        # Check if any test run happened after the last write
        test_after_write = False
        for entry in entries[last_write_idx + 1 :]:
            if entry.action == "SHELL" and ("pytest" in entry.target or "python3 -m pytest" in entry.target):
                test_after_write = True
                break

        if not test_after_write:
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

        if not entries:
            return issues

        last_write_idx = -1
        for i, entry in enumerate(entries):
            if entry.action == "WRITE":
                last_write_idx = i

        if last_write_idx == -1:
            return issues

        drift_after = False
        for entry in entries[last_write_idx + 1 :]:
            if entry.action in ("SHELL", "CHECK") and "drifter check" in entry.target:
                drift_after = True
                break

        if not drift_after:
            issues.append(Issue(
                check=self.name,
                file="session.log",
                detail="Last WRITE not followed by 'drifter check'",
                severity="error",
            ))
        return issues


class NoRushCheck:
    """Verify at least one drift check per 3 WRITEs."""

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
                severity="warn",
            ))
        elif write_count > 0:
            ratio = write_count / max(drift_count, 1)
            if ratio > 3:
                issues.append(Issue(
                    check=self.name,
                    file="session.log",
                    detail=f"{write_count} WRITEs vs {drift_count} drift checks (ratio {ratio:.1f}:1) — max 3:1",
                    severity="warn",
                ))
        return issues

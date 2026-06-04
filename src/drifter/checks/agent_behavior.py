from __future__ import annotations

import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from drifter._toml_utils import safe_load_toml
from drifter.checks._base import Check, Issue
from drifter.config import Config
from drifter.history_reader import HistoryReader

class AgentSelfAuditCheck:
    """Scan agent shell history for dangerous commands."""

    name = "agent_self_audit"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        patterns_file = root / "dangerous_patterns.toml"
        if not patterns_file.exists():
            return issues

        data = safe_load_toml(patterns_file)
        if data is None:
            issues.append(Issue(
                check=self.name,
                file="dangerous_patterns.toml",
                detail="Cannot parse dangerous_patterns.toml — file may be corrupted",
                severity="error",
            ))
            return issues

        agent_rules = data.get("agent", {})
        always_report = agent_rules.get("always_report", [])
        approval_required = agent_rules.get("approval_required", [])

        if not config.history_path:
            return issues
        reader = HistoryReader(Path(config.history_path).expanduser())
        if not reader.path.exists():
            return issues

        # Wrap history read in a timeout to avoid DoS from huge files
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(reader.read_commands, max_entries=50)
                recent = future.result(timeout=10)
        except Exception:
            issues.append(Issue(
                check=self.name,
                file=str(reader.path),
                detail="Timeout reading shell history — file may be too large",
                severity="warn",
            ))
            return issues

        for line in recent:
            line = line.strip()
            if not line:
                continue
            lower = line.lower()
            for pattern in always_report:
                if pattern.lower() in lower:
                    issues.append(Issue(check=self.name, file=str(reader.path), detail=f"Agent ran '{pattern}' without approval: '{line[:80]}'", severity="error"))
            for pattern in approval_required:
                if pattern.lower() in lower:
                    issues.append(Issue(check=self.name, file=str(reader.path), detail=f"Agent ran '{pattern}' without logged approval: '{line[:80]}'", severity="warn"))
        return issues

class GitCommitApprovalCheck:
    """Verify recent commits have approval markers.

    Checks the last N commits (default 5) for unapproved destructive
    changes rather than only the most recent commit.
    """

    name = "git_commit_approval"
    COMMIT_CHECK_WINDOW = 5
    _DESTRUCTIVE_RE = re.compile(
        r"\b(delete|remove|drop|destroy|rm -rf)\b",
        re.IGNORECASE,
    )

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        try:
            # Verify root is actually a git repo before checking log
            repo_check = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "--git-dir"],
                capture_output=True, text=True, timeout=5,
            )
            if repo_check.returncode != 0:
                return issues

            result = subprocess.run(
                ["git", "-C", str(root), "log", f"-{self.COMMIT_CHECK_WINDOW}", "--pretty=%H|%s|%B%x00"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return issues

            commits = result.stdout.split("\x00")
            unapproved_destructive: list[str] = []
            for commit_block in commits:
                if "|" not in commit_block:
                    continue
                parts = commit_block.split("|", 2)
                if len(parts) < 2:
                    continue
                hash_short, subject = parts[0][:7], parts[1]
                has_marker = "[APPROVED BY" in commit_block.upper()
                is_destructive = bool(self._DESTRUCTIVE_RE.search(subject))
                if is_destructive and not has_marker:
                    unapproved_destructive.append(f"{hash_short}: {subject}")

            if unapproved_destructive:
                issues.append(Issue(
                    check=self.name,
                    file="git",
                    detail=f"Unapproved destructive commits: {unapproved_destructive}",
                    severity="error",
                ))
        except Exception:
            pass
        return issues

from __future__ import annotations
import subprocess

import re
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from drifter.checks._base import Check, Issue
from drifter.config import Config

class AgentSelfAuditCheck:
    """Scan agent bash history for dangerous commands."""

    name = "agent_self_audit"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        patterns_file = root / "dangerous_patterns.toml"
        if not patterns_file.exists():
            return issues

        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib
        with patterns_file.open("rb") as f:
            data = tomllib.load(f)

        agent_rules = data.get("agent", {})
        always_report = agent_rules.get("always_report", [])
        approval_required = agent_rules.get("approval_required", [])

        history_path = Path.home() / ".bash_history"
        if not history_path.exists():
            return issues

        lines = history_path.read_text(encoding="utf-8").strip().split("\n")
        recent = lines[-50:] if len(lines) > 50 else lines

        for line in recent:
            line = line.strip()
            if not line:
                continue
            lower = line.lower()
            for pattern in always_report:
                if pattern.lower() in lower:
                    issues.append(Issue(
                        check=self.name,
                        file="~/.bash_history",
                        detail=f"Agent ran '{pattern}' without approval: '{line[:80]}'",
                        severity="error",
                    ))
            for pattern in approval_required:
                if pattern.lower() in lower:
                    issues.append(Issue(
                        check=self.name,
                        file="~/.bash_history",
                        detail=f"Agent ran '{pattern}' without logged approval: '{line[:80]}'",
                        severity="warn",
                    ))
        return issues

class GitCommitApprovalCheck:
    """Verify last commit has approval marker."""

    name = "git_commit_approval"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "log", "-1", "--pretty=%B"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return issues
            msg = result.stdout.strip()
            if not msg:
                return issues
            has_marker = (
                "[APPROVED BY" in msg.upper() or
                msg.upper().startswith("APPROVED BY")
            )
            if not has_marker:
                issues.append(Issue(
                    check=self.name,
                    file="git",
                    detail=f"Last commit lacks approval marker. Message: '{msg[:60]}...'",
                    severity="error",
                ))
        except Exception:
            pass
        return issues

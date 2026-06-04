from __future__ import annotations
import subprocess
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

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

        with patterns_file.open("rb") as f:
            data = tomllib.load(f)

        agent_rules = data.get("agent", {})
        always_report = agent_rules.get("always_report", [])
        approval_required = agent_rules.get("approval_required", [])

        if not config.history_path:
            return issues
        reader = HistoryReader(Path(config.history_path).expanduser())
        if not reader.path.exists():
            return issues

        recent = reader.read_commands(max_entries=50)

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
    """Verify last commit has approval marker."""

    name = "git_commit_approval"

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

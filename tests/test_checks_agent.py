"""Tests for agent behavior checks (checks/agent_behavior.py)."""

from pathlib import Path

from drifter.config import Config
from drifter.checks.agent_behavior import AgentSelfAuditCheck, GitCommitApprovalCheck


class TestAgentSelfAuditCheck:
    def test_detects_blocked_command(self, tmp_path: Path) -> None:
        config = Config.load(
            root=tmp_path,
            overrides={"history_path": str(tmp_path / ".bash_history")},
        )
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text(
            '[agent]\nalways_report = ["git commit"]\napproval_required = ["sudo"]\n'
        )
        fake_history = tmp_path / ".bash_history"
        fake_history.write_text("git commit -m 'test'\n")
        check = AgentSelfAuditCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "git commit" in issues[0].detail
        assert issues[0].severity == "error"

    def test_no_history_no_crash(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text('[agent]\nalways_report = ["git commit"]\n')
        check = AgentSelfAuditCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_history_path_disabled_by_default(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text('[agent]\nalways_report = ["git commit"]\n')
        # Create a fake bash history even though config has no history_path
        fake_history = tmp_path / ".bash_history"
        fake_history.write_text("git commit -m 'test'\n")
        check = AgentSelfAuditCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestGitCommitApprovalCheck:
    def test_missing_approval_marker_destructive(self, git_repo) -> None:
        config = Config.load(root=git_repo.path)
        git_repo.commit("delete old files")

        check = GitCommitApprovalCheck()
        issues = check.run(git_repo.path, config)
        assert len(issues) == 1
        assert "Unapproved destructive commits" in issues[0].detail

    def test_benign_commit_without_marker_ok(self, git_repo) -> None:
        config = Config.load(root=git_repo.path)
        git_repo.commit("no approval")

        check = GitCommitApprovalCheck()
        issues = check.run(git_repo.path, config)
        assert len(issues) == 0

    def test_with_approval_marker(self, git_repo) -> None:
        config = Config.load(root=git_repo.path)
        git_repo.commit("[APPROVED BY MAINTAINER] fix bug")

        check = GitCommitApprovalCheck()
        issues = check.run(git_repo.path, config)
        assert len(issues) == 0

    def test_no_git_repo(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        check = GitCommitApprovalCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

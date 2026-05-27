"""Tests for behavior and audit checks."""

from pathlib import Path

from drifter.config import Config
from drifter.checks.agent_behavior import AgentSelfAuditCheck, GitCommitApprovalCheck
from drifter.checks.code_quality import TomllibCompatibilityCheck
from drifter.checks.sync import AuditCoverageCheck, ReporterCompletenessCheck
from drifter.drift_guard import run_checks


class TestAgentSelfAuditCheck:
    def test_detects_blocked_command(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text(
            '[agent]\nalways_report = ["git commit"]\napproval_required = ["sudo"]\n'
        )
        import os
        fake_history = tmp_path / ".bash_history"
        fake_history.write_text("git commit -m 'test'\n")
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = str(tmp_path)
        try:
            check = AgentSelfAuditCheck()
            issues = check.run(tmp_path, config)
            assert len(issues) == 1
            assert "git commit" in issues[0].detail
            assert issues[0].severity == "error"
        finally:
            if old_home is not None:
                os.environ["HOME"] = old_home
            else:
                del os.environ["HOME"]

    def test_no_history_no_crash(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text('[agent]\nalways_report = ["git commit"]\n')
        import os
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = str(tmp_path)
        try:
            check = AgentSelfAuditCheck()
            issues = check.run(tmp_path, config)
            assert len(issues) == 0
        finally:
            if old_home is not None:
                os.environ["HOME"] = old_home
            else:
                del os.environ["HOME"]


class TestGitCommitApprovalCheck:
    def test_missing_approval_marker(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        import subprocess
        subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True, check=True)
        (tmp_path / "file.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "no approval"], cwd=str(tmp_path), capture_output=True, check=True)

        check = GitCommitApprovalCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "lacks approval marker" in issues[0].detail

    def test_with_approval_marker(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        import subprocess
        subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True, check=True)
        (tmp_path / "file.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "[APPROVED BY HOX] fix bug"], cwd=str(tmp_path), capture_output=True, check=True)

        check = GitCommitApprovalCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_no_git_repo(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        check = GitCommitApprovalCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestTomllibCompatibilityCheck:
    def test_detects_bare_tomllib(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "drifter" / "foo.py"
        src.parent.mkdir(parents=True)
        src.write_text("import tomllib\n")
        check = TomllibCompatibilityCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "bare 'import tomllib'" in issues[0].detail

    def test_allows_guarded_tomllib(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "drifter" / "foo.py"
        src.parent.mkdir(parents=True)
        src.write_text(
            "import sys\n"
            "if sys.version_info >= (3, 11):\n"
            "    import tomllib\n"
            "else:\n"
            "    import tomli as tomllib\n"
        )
        check = TomllibCompatibilityCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestAuditCoverageCheck:
    def test_missing_warn_action(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        cli = tmp_path / "src" / "drifter" / "cli.py"
        cli.parent.mkdir(parents=True)
        cli.write_text(
            'def cmd_audit(args):\n'
            '    if classification.action in ("block", "approval_required"):\n'
            '        violations.append((line, classification))\n'
        )
        guard = tmp_path / "src" / "drifter" / "shell_guard.py"
        guard.parent.mkdir(parents=True, exist_ok=True)
        guard.write_text(
            'action="block"\n'
            'action="approval_required"\n'
            'action="warn"\n'
        )
        check = AuditCoverageCheck()
        issues = check.run(tmp_path, config)
        assert any("'warn'" in i.detail for i in issues)

    def test_all_actions_covered(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        cli = tmp_path / "src" / "drifter" / "cli.py"
        cli.parent.mkdir(parents=True)
        cli.write_text(
            'def cmd_audit(args):\n'
            '    if classification.action in ("block", "approval_required", "warn"):\n'
            '        violations.append((line, classification))\n'
        )
        guard = tmp_path / "src" / "drifter" / "shell_guard.py"
        guard.parent.mkdir(parents=True, exist_ok=True)
        guard.write_text(
            'action="block"\n'
            'action="approval_required"\n'
            'action="warn"\n'
        )
        check = AuditCoverageCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestReporterCompletenessCheck:
    def test_missing_info_severity(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        cli = tmp_path / "src" / "drifter" / "cli.py"
        cli.parent.mkdir(parents=True)
        cli.write_text(
            'def _format_issues_console(issues, score=None):\n'
            '    for issue in issues:\n'
            '        if issue.severity == "error":\n'
            '            print(f"ERROR: {issue}")\n'
            '        elif issue.severity == "warn":\n'
            '            print(f"WARN: {issue}")\n'
        )
        check = ReporterCompletenessCheck()
        issues = check.run(tmp_path, config)
        assert any("'info'" in i.detail for i in issues)

    def test_all_severities_present(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        cli = tmp_path / "src" / "drifter" / "cli.py"
        cli.parent.mkdir(parents=True)
        cli.write_text(
            'def _format_issues_console(issues, score=None):\n'
            '    errors = [i for i in issues if i.severity == "error"]\n'
            '    warns = [i for i in issues if i.severity == "warn"]\n'
            '    infos = [i for i in issues if i.severity == "info"]\n'
        )
        check = ReporterCompletenessCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0



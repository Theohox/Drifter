"""Tests for shell guard classifier."""

from pathlib import Path

from drifter.shell_guard import ShellGuard


class TestShellGuard:
    def test_blocks_git_commit(self, tmp_path: Path) -> None:
        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text("""
[git]
always_block = ["git commit"]
allowed = ["git status"]
approval_required = ["git add"]
""")
        guard = ShellGuard(root=tmp_path)

        result = guard.classify("git commit -m 'test'")
        assert result.action == "block"
        assert "git commit" in result.matched_pattern

    def test_allows_git_status(self, tmp_path: Path) -> None:
        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text("""
[git]
always_block = ["git commit"]
allowed = ["git status"]
approval_required = ["git add"]
""")
        guard = ShellGuard(root=tmp_path)

        result = guard.classify("git status")
        assert result.action == "allow"

    def test_requires_approval_for_git_add(self, tmp_path: Path) -> None:
        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text("""
[git]
always_block = ["git commit"]
allowed = ["git status"]
approval_required = ["git add"]
""")
        guard = ShellGuard(root=tmp_path)

        result = guard.classify("git add file.py")
        assert result.action == "approval_required"

    def test_blocks_shell_pattern(self, tmp_path: Path) -> None:
        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text("""
[shell]
blocked = ["rm -rf /"]
confirm_required = ["sudo"]
""")
        guard = ShellGuard(root=tmp_path)

        result = guard.classify("rm -rf /")
        assert result.action == "block"

    def test_warns_on_confirm_required(self, tmp_path: Path) -> None:
        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text("""
[shell]
blocked = ["rm -rf /"]
confirm_required = ["sudo"]
""")
        guard = ShellGuard(root=tmp_path)

        result = guard.classify("sudo apt install python3")
        assert result.action == "warn"

    def test_check_human_readable(self, tmp_path: Path) -> None:
        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text("""
[git]
always_block = ["git commit"]
""")
        guard = ShellGuard(root=tmp_path)

        assert "BLOCKED" in guard.check("git commit -m x")
        assert "ALLOWED" in guard.check("echo hello")

    def test_missing_patterns_file(self, tmp_path: Path) -> None:
        guard = ShellGuard(root=tmp_path)
        result = guard.classify("git commit")
        # Should allow everything if no patterns file exists
        assert result.action == "allow"

    def test_blocks_system_dir(self, tmp_path: Path) -> None:
        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text("""
[filesystem]
system_dirs = ["/etc"]
sensitive_patterns = [".env"]
""")
        guard = ShellGuard(root=tmp_path)

        result = guard.classify("cat /etc/passwd")
        assert result.action == "block"
        assert "/etc" in result.matched_pattern

    def test_requires_approval_for_sensitive(self, tmp_path: Path) -> None:
        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text("""
[filesystem]
system_dirs = ["/etc"]
sensitive_patterns = [".env"]
""")
        guard = ShellGuard(root=tmp_path)

        result = guard.classify("cat .env")
        assert result.action == "approval_required"
        assert ".env" in result.matched_pattern


class TestShellGuardEnforce:
    def test_enforce_raises_on_blocked_command(self, tmp_path: Path) -> None:
        from drifter.errors import DangerousCommandError

        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text("""
[git]
always_block = ["git commit"]
""")
        guard = ShellGuard(root=tmp_path)

        with pytest.raises(DangerousCommandError) as exc_info:
            guard.enforce("git commit -m 'test'")
        assert "git commit" in str(exc_info.value)
        assert exc_info.value.command == "git commit -m 'test'"
        assert exc_info.value.pattern == "git commit"

    def test_enforce_raises_on_approval_required(self, tmp_path: Path) -> None:
        from drifter.errors import ApprovalRequiredError

        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text("""
[git]
approval_required = ["git add"]
""")
        guard = ShellGuard(root=tmp_path)

        with pytest.raises(ApprovalRequiredError) as exc_info:
            guard.enforce("git add file.py")
        assert "git add" in str(exc_info.value)
        assert exc_info.value.command == "git add file.py"

    def test_enforce_returns_on_allowed(self, tmp_path: Path) -> None:
        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text("""
[git]
allowed = ["git status"]
""")
        guard = ShellGuard(root=tmp_path)

        result = guard.enforce("git status")
        assert result.action == "allow"

    def test_enforce_returns_on_warn(self, tmp_path: Path) -> None:
        import warnings

        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text("""
[shell]
confirm_required = ["sudo"]
""")
        guard = ShellGuard(root=tmp_path)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = guard.enforce("sudo apt install python3")
            assert result.action == "warn"
            assert len(w) == 1
            assert "DANGEROUS COMMAND WARNING" in str(w[0].message)

    def test_enforce_blocked_never_reaches_subprocess(self, tmp_path: Path) -> None:
        from unittest.mock import patch
        from drifter.errors import DangerousCommandError

        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text("""
[git]
always_block = ["git commit"]
""")
        guard = ShellGuard(root=tmp_path)

        with patch("subprocess.run") as mock_run:
            with pytest.raises(DangerousCommandError):
                guard.enforce("git commit -m x")
            mock_run.assert_not_called()


import pytest

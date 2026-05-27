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

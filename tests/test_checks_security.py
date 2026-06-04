"""Tests for security checks: GitSafetyCheck and DangerousPatternsCheck."""

from __future__ import annotations

from pathlib import Path

from drifter.config import Config
from drifter.checks.security import (
    CredentialLeakCheck,
    DangerousPatternsCheck,
    GitSafetyCheck,
)


class TestGitSafetyCheck:
    def test_detects_git_commit_in_subprocess(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "main.py"
        src.parent.mkdir(parents=True)
        src.write_text('os.system("git commit -m fix")\n')
        check = GitSafetyCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) >= 1
        assert any("git commit" in i.detail for i in issues)

    def test_detects_git_push_in_string(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "main.py"
        src.parent.mkdir(parents=True)
        src.write_text('cmd = "git push origin main"\n')
        check = GitSafetyCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "git push" in issues[0].detail

    def test_allows_safe_git_commands(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "main.py"
        src.parent.mkdir(parents=True)
        src.write_text('subprocess.run(["git", "status"])\n')
        check = GitSafetyCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_skips_comments(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "main.py"
        src.parent.mkdir(parents=True)
        src.write_text("# git commit is blocked\n")
        check = GitSafetyCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_skips_tests_directory(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        test_file = tmp_path / "tests" / "test_foo.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text('subprocess.run(["git", "commit", "-m", "x"])\n')
        check = GitSafetyCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestDangerousPatternsCheck:
    def test_missing_file(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        check = DangerousPatternsCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "does not exist" in issues[0].detail

    def test_invalid_toml(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text("not valid toml [[[")
        check = DangerousPatternsCheck()
        issues = check.run(tmp_path, config)
        assert any("Invalid TOML" in i.detail for i in issues)

    def test_missing_git_section(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text("[shell]\nblocked = []\n")
        check = DangerousPatternsCheck()
        issues = check.run(tmp_path, config)
        assert any("Missing [git]" in i.detail for i in issues)

    def test_missing_shell_section(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text("[git]\nalways_block = []\n")
        check = DangerousPatternsCheck()
        issues = check.run(tmp_path, config)
        assert any("Missing [shell]" in i.detail for i in issues)

    def test_agents_md_missing_reference(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text("[git]\nalways_block = []\n[shell]\nblocked = []\n")
        agents = tmp_path / "AGENTS.md"
        agents.write_text("no reference to the patterns file here\n")
        check = DangerousPatternsCheck()
        issues = check.run(tmp_path, config)
        assert any("AGENTS.md does not reference" in i.detail for i in issues)

    def test_valid_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text("[git]\nalways_block = []\n[shell]\nblocked = []\n")
        agents = tmp_path / "AGENTS.md"
        agents.write_text("references dangerous_patterns.toml here\n")
        check = DangerousPatternsCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestCredentialLeakCheck:
    def test_detects_openai_key(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "main.py"
        src.parent.mkdir(parents=True)
        src.write_text('api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"\n')
        check = CredentialLeakCheck()
        issues = check.run(tmp_path, config)
        assert any("OpenAI" in i.detail for i in issues)

    def test_detects_url_with_credentials(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "main.py"
        src.parent.mkdir(parents=True)
        src.write_text('url = "https://user:secret123@example.com/path"\n')
        check = CredentialLeakCheck()
        issues = check.run(tmp_path, config)
        assert any("embedded credentials" in i.detail for i in issues)

    def test_detects_aws_key(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "main.py"
        src.parent.mkdir(parents=True)
        src.write_text('aws_access_key = "AKIAIOSFODNN7ABCDEFG"\n')
        check = CredentialLeakCheck()
        issues = check.run(tmp_path, config)
        assert any("AWS" in i.detail for i in issues)

    def test_detects_pem_key(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "main.py"
        src.parent.mkdir(parents=True)
        src.write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n")
        check = CredentialLeakCheck()
        issues = check.run(tmp_path, config)
        assert any("Private key" in i.detail for i in issues)

    def test_skips_comments(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "main.py"
        src.parent.mkdir(parents=True)
        src.write_text('# api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"\n')
        check = CredentialLeakCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_skips_tests_directory(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        test_file = tmp_path / "tests" / "test_foo.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text('api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"\n')
        check = CredentialLeakCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

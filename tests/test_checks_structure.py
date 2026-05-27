"""Tests for structural checks."""

from pathlib import Path

from drifter.config import Config
from drifter.checks.sync import CliOutputCheck
from drifter.checks.security import GitignoreCheck
from drifter.checks.structure import (
    ClaimSyncCheck,
    FileSizeCheck,
    ManifestSyncCheck,
    TreeIntegrityCheck,
)


class TestCliOutputCheck:
    def test_missing_mention(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        cli = tmp_path / "src" / "drifter" / "cli.py"
        cli.parent.mkdir(parents=True)
        cli.write_text(
            'def cmd_init(args):\n'
            '    print("AGENTS.md")\n'
            '    print("session-protocol.md")\n'
            '    print("project-conductor.md")\n'
        )
        check = CliOutputCheck()
        issues = check.run(tmp_path, config)
        assert any("dangerous_patterns.toml" in i.detail for i in issues)

    def test_all_mentions_present(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        cli = tmp_path / "src" / "drifter" / "cli.py"
        cli.parent.mkdir(parents=True)
        cli.write_text(
            'def cmd_init(args):\n'
            '    print("AGENTS.md")\n'
            '    print("dangerous_patterns.toml")\n'
            '    print("session-protocol.md")\n'
            '    print("project-conductor.md")\n'
        )
        check = CliOutputCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestGitignoreCheck:
    def test_missing_gitignore(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        check = GitignoreCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "does not exist" in issues[0].detail

    def test_sensitive_file_not_ignored(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        (tmp_path / ".gitignore").write_text("*.pyc\n")
        (tmp_path / ".env").write_text("SECRET=123\n")
        (tmp_path / "dangerous_patterns.toml").write_text(
            '[filesystem]\nsensitive_patterns = [".env"]\n'
        )
        check = GitignoreCheck()
        issues = check.run(tmp_path, config)
        assert any(".env" in i.detail for i in issues)

    def test_sensitive_file_ignored(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        (tmp_path / ".gitignore").write_text(".env\n")
        (tmp_path / ".env").write_text("SECRET=123\n")
        check = GitignoreCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestTreeIntegrityCheck:
    def test_orphan_file(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        manifest = tmp_path / "drifter-manifest.toml"
        manifest.write_text('[tree.src]\n"foo.py" = {}\n')
        orphan = tmp_path / "bar.py"
        orphan.write_text("# orphan")
        check = TreeIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert any("bar.py" in i.file and "not declared" in i.detail for i in issues)

    def test_missing_file(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        manifest = tmp_path / "drifter-manifest.toml"
        manifest.write_text('[tree.src]\n"missing.py" = {}\n')
        check = TreeIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert any("missing.py" in i.file and "missing from disk" in i.detail for i in issues)


class TestFileSizeCheck:
    def test_oversized_file(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        manifest = tmp_path / "drifter-manifest.toml"
        manifest.write_text('[structure]\nmax_file_lines = 5\n[tree.src]\n"big.py" = {}\n')
        src = tmp_path / "src"
        src.mkdir()
        big = src / "big.py"
        big.write_text("\n".join(["x"] * 10))
        check = FileSizeCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "10 lines exceeds max 5" in issues[0].detail

    def test_file_within_limit(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        manifest = tmp_path / "drifter-manifest.toml"
        manifest.write_text('[structure]\nmax_file_lines = 100\n[tree.src]\n"small.py" = {}\n')
        src = tmp_path / "src"
        src.mkdir()
        small = src / "small.py"
        small.write_text("x\n")
        check = FileSizeCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0


class TestManifestSyncCheck:
    def test_count_mismatch(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        manifest = tmp_path / "drifter-manifest.toml"
        manifest.write_text('[checks]\ncount = 999\nnames = ["stale_reference"]\n')
        check = ManifestSyncCheck()
        issues = check.run(tmp_path, config)
        assert any("declares 999 checks" in i.detail for i in issues)


class TestClaimSyncCheck:
    def test_stale_claim(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        manifest = tmp_path / "drifter-manifest.toml"
        manifest.write_text(
            '[checks]\ncount = 42\n'
            '[claims]\n"README.md" = [{ pattern = "{count} checks", value = "checks.count" }]\n'
        )
        readme = tmp_path / "README.md"
        readme.write_text("We have 5 checks.\n")
        check = ClaimSyncCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "has 5 but manifest expects 42" in issues[0].detail

    def test_synced_claim_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        manifest = tmp_path / "drifter-manifest.toml"
        manifest.write_text(
            '[checks]\ncount = 5\n'
            '[claims]\n"README.md" = [{ pattern = "{count} checks", value = "checks.count" }]\n'
        )
        readme = tmp_path / "README.md"
        readme.write_text("We have 5 checks.\n")
        check = ClaimSyncCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

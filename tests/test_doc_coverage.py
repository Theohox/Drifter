"""Tests for doc coverage check."""

from pathlib import Path

from drifter.config import Config
from drifter.checks.sync import DocCoverageCheck


class TestDocCoverageCheck:
    def test_agents_md_missing_module(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        # Create AGENTS.md without any module mentions
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            "# Agent Contract\n\n## 2. Architecture\n\n| Component | Location |\n|---|---|\n"
        )
        # Create src/drifter/fancy_module.py
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        (src / "fancy_module.py").write_text("x = 1\n")
        (src / "__init__.py").write_text("")
        (src / "_base.py").write_text("")
        # No cli.py needed for this test
        (src / "cli.py").write_text("subparsers.add_parser('check')\n")

        check = DocCoverageCheck()
        issues = check.run(tmp_path, config)
        assert any("fancy_module.py" in i.detail for i in issues)

    def test_agents_md_has_all_modules(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        (src / "fancy_module.py").write_text("x = 1\n")
        (src / "__init__.py").write_text("")
        (src / "_base.py").write_text("")
        (src / "cli.py").write_text("subparsers.add_parser('check')\n")

        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            "# Agent Contract\n\n## 2. Architecture\n\n"
            "| Component | Location |\n|---|---|\n"
            "| Fancy | `src/drifter/fancy_module.py` |\n"
            "\n## 9. Quick Reference\n\n"
            "```bash\ndrifter check\n```\n"
        )

        check = DocCoverageCheck()
        issues = check.run(tmp_path, config)
        assert not any("fancy_module.py" in i.detail for i in issues)

    def test_quick_reference_missing_command(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        (src / "cli.py").write_text(
            'subparsers.add_parser("check", help="Run drift guard")\n'
            'subparsers.add_parser("preflight", help="Run pre-flight checklist")\n'
        )
        (src / "__init__.py").write_text("")
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            "# Agent Contract\n\n## 9. Quick Reference\n\n```bash\ndrifter check\n```\n"
        )
        readme = tmp_path / "README.md"
        readme.write_text(
            "# Project\n\nenforcement dangerous_patterns session audit pre-flight conductor\n"
        )

        check = DocCoverageCheck()
        issues = check.run(tmp_path, config)
        assert any("drifter preflight" in i.detail for i in issues)

    def test_quick_reference_has_all_commands(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        (src / "cli.py").write_text(
            'subparsers.add_parser("check", help="Run drift guard")\n'
            'subparsers.add_parser("preflight", help="Run pre-flight checklist")\n'
        )
        (src / "__init__.py").write_text("")
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            "# Agent Contract\n\n## 9. Quick Reference\n\n"
            "```bash\ndrifter check\ndrifter preflight\n```\n"
        )
        readme = tmp_path / "README.md"
        readme.write_text(
            "# Project\n\nenforcement dangerous_patterns session audit pre-flight conductor\n"
        )

        check = DocCoverageCheck()
        issues = check.run(tmp_path, config)
        assert not any("drifter preflight" in i.detail for i in issues)

    def test_readme_missing_feature(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        (src / "cli.py").write_text("subparsers.add_parser('check')\n")
        (src / "__init__.py").write_text("")
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            "# Agent Contract\n\n## 9. Quick Reference\n\n```bash\ndrifter check\n```\n"
        )
        readme = tmp_path / "README.md"
        readme.write_text("# Project\n\nSome text.\n")

        check = DocCoverageCheck()
        issues = check.run(tmp_path, config)
        # Should warn about missing features like "enforcement", "session audit", etc.
        assert any("enforcement" in i.detail for i in issues)

    def test_template_divergence(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "dangerous_patterns.toml").write_text("[git]\nalways_block = []\n")
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "dangerous_patterns.toml.tmpl").write_text(
            '[git]\nalways_block = ["git commit"]\n'
        )
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        (src / "cli.py").write_text("subparsers.add_parser('check')\n")
        (src / "__init__.py").write_text("")
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            "# Agent Contract\n\n## 9. Quick Reference\n\n```bash\ndrifter check\n```\n"
        )
        readme = tmp_path / "README.md"
        readme.write_text(
            "# Project\n\nenforcement dangerous_patterns session audit pre-flight conductor\n"
        )

        check = DocCoverageCheck()
        issues = check.run(tmp_path, config)
        assert any(
            "dangerous_patterns.toml" in i.file and "diverges from template" in i.detail
            for i in issues
        )

    def test_template_in_sync(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "dangerous_patterns.toml").write_text("[git]\nalways_block = []\n")
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "dangerous_patterns.toml.tmpl").write_text(
            "[git]\nalways_block = []\n"
        )
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        (src / "cli.py").write_text("subparsers.add_parser('check')\n")
        (src / "__init__.py").write_text("")
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            "# Agent Contract\n\n## 9. Quick Reference\n\n```bash\ndrifter check\n```\n"
        )
        readme = tmp_path / "README.md"
        readme.write_text(
            "# Project\n\nenforcement dangerous_patterns session audit pre-flight conductor\n"
        )

        check = DocCoverageCheck()
        issues = check.run(tmp_path, config)
        assert not any(
            "dangerous_patterns.toml" in i.file and "diverges from template" in i.detail
            for i in issues
        )

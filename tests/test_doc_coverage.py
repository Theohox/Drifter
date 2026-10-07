"""Tests for doc coverage check."""

from drifter.config import Config
from drifter.checks.sync import DocCoverageCheck

FULL_README = (
    "# Project\n\nenforcement dangerous_patterns session audit pre-flight conductor\n"
)


class TestDocCoverageCheck:
    def test_agents_md_missing_module(self, minimal_project) -> None:
        root = minimal_project(
            agents="# Agent Contract\n\n## 2. Architecture\n\n| Component | Location |\n|---|---|\n"
        )
        config = Config.load(root=root)
        src = root / "src" / "drifter"
        (src / "fancy_module.py").write_text("x = 1\n")
        (src / "_base.py").write_text("")

        check = DocCoverageCheck()
        issues = check.run(root, config)
        assert any("fancy_module.py" in i.detail for i in issues)

    def test_agents_md_has_all_modules(self, minimal_project) -> None:
        root = minimal_project(
            agents=(
                "# Agent Contract\n\n## 2. Architecture\n\n"
                "| Component | Location |\n|---|---|\n"
                "| Fancy | `src/drifter/fancy_module.py` |\n"
                "\n## 9. Quick Reference\n\n"
                "```bash\ndrifter check\n```\n"
            )
        )
        config = Config.load(root=root)
        src = root / "src" / "drifter"
        (src / "fancy_module.py").write_text("x = 1\n")
        (src / "_base.py").write_text("")

        check = DocCoverageCheck()
        issues = check.run(root, config)
        assert not any("fancy_module.py" in i.detail for i in issues)

    def test_quick_reference_missing_command(self, minimal_project) -> None:
        root = minimal_project(
            cli=(
                'subparsers.add_parser("check", help="Run drift guard")\n'
                'subparsers.add_parser("preflight", help="Run pre-flight checklist")\n'
            ),
            agents=(
                "# Agent Contract\n\n## 9. Quick Reference\n\n```bash\ndrifter check\n```\n"
            ),
            readme=FULL_README,
        )
        config = Config.load(root=root)

        check = DocCoverageCheck()
        issues = check.run(root, config)
        assert any("drifter preflight" in i.detail for i in issues)

    def test_quick_reference_has_all_commands(self, minimal_project) -> None:
        root = minimal_project(
            cli=(
                'subparsers.add_parser("check", help="Run drift guard")\n'
                'subparsers.add_parser("preflight", help="Run pre-flight checklist")\n'
            ),
            agents=(
                "# Agent Contract\n\n## 9. Quick Reference\n\n"
                "```bash\ndrifter check\ndrifter preflight\n```\n"
            ),
            readme=FULL_README,
        )
        config = Config.load(root=root)

        check = DocCoverageCheck()
        issues = check.run(root, config)
        assert not any("drifter preflight" in i.detail for i in issues)

    def test_readme_missing_feature(self, minimal_project) -> None:
        root = minimal_project(
            agents=(
                "# Agent Contract\n\n## 9. Quick Reference\n\n```bash\ndrifter check\n```\n"
            ),
            readme="# Project\n\nSome text.\n",
        )
        config = Config.load(root=root)

        check = DocCoverageCheck()
        issues = check.run(root, config)
        # Should warn about missing features like "enforcement", "session audit", etc.
        assert any("enforcement" in i.detail for i in issues)

    def test_template_divergence(self, minimal_project) -> None:
        root = minimal_project(
            agents=(
                "# Agent Contract\n\n## 9. Quick Reference\n\n```bash\ndrifter check\n```\n"
            ),
            readme=FULL_README,
        )
        config = Config.load(root=root)
        (root / "dangerous_patterns.toml").write_text("[git]\nalways_block = []\n")
        templates = root / "src" / "drifter" / "templates"
        templates.mkdir(parents=True)
        (templates / "dangerous_patterns.toml.tmpl").write_text(
            '[git]\nalways_block = ["git commit"]\n'
        )

        check = DocCoverageCheck()
        issues = check.run(root, config)
        assert any(
            "dangerous_patterns.toml" in i.file and "diverges from template" in i.detail
            for i in issues
        )

    def test_template_in_sync(self, minimal_project) -> None:
        root = minimal_project(
            agents=(
                "# Agent Contract\n\n## 9. Quick Reference\n\n```bash\ndrifter check\n```\n"
            ),
            readme=FULL_README,
        )
        config = Config.load(root=root)
        (root / "dangerous_patterns.toml").write_text("[git]\nalways_block = []\n")
        templates = root / "src" / "drifter" / "templates"
        templates.mkdir(parents=True)
        (templates / "dangerous_patterns.toml.tmpl").write_text(
            "[git]\nalways_block = []\n"
        )

        check = DocCoverageCheck()
        issues = check.run(root, config)
        assert not any(
            "dangerous_patterns.toml" in i.file and "diverges from template" in i.detail
            for i in issues
        )

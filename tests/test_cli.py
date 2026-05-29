"""Tests for CLI commands."""

from pathlib import Path
from unittest.mock import MagicMock

from drifter.cli import cmd_init


class TestCmdInit:
    def test_creates_all_files(self, tmp_path: Path) -> None:
        args = MagicMock()
        args.root = str(tmp_path)
        args.force = False
        args.full = False
        cmd_init(args)
        assert (tmp_path / "AGENTS.md").exists()
        assert (tmp_path / "dangerous_patterns.toml").exists()
        assert (tmp_path / "docs" / "session-protocol.md").exists()
        assert (tmp_path / "docs" / "project-conductor.md").exists()
        assert (tmp_path / "docs" / "archive").is_dir()

    def test_mentions_all_canonical_files(self, tmp_path: Path) -> None:
        args = MagicMock()
        args.root = str(tmp_path)
        args.force = False
        args.full = False
        import io
        import sys

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            cmd_init(args)
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        assert "AGENTS.md" in output
        assert "dangerous_patterns.toml" in output
        assert "session-protocol.md" in output
        assert "project-conductor.md" in output

    def test_template_substitution(self, tmp_path: Path) -> None:
        args = MagicMock()
        args.root = str(tmp_path)
        args.force = False
        args.full = False
        cmd_init(args)

        # Project name substituted in AGENTS.md
        agents = (tmp_path / "AGENTS.md").read_text()
        assert "{{PROJECT_NAME}}" not in agents
        assert tmp_path.name in agents

        # NOW substituted in drifter.toml comment
        toml = (tmp_path / "drifter.toml").read_text()
        assert "{{NOW}}" not in toml
        assert "{{PROJECT_NAME}}" not in toml
        assert tmp_path.name in toml

    def test_no_phantom_references_in_agents(self, tmp_path: Path) -> None:
        args = MagicMock()
        args.root = str(tmp_path)
        args.force = False
        args.full = False
        cmd_init(args)

        agents = (tmp_path / "AGENTS.md").read_text()
        # AGENTS.md references canonical docs; init must create them so refs are not phantom
        assert "docs/methodology.md" in agents
        assert "docs/architecture.md" in agents
        assert "docs/adoption-guide.md" in agents
        assert "docs/rules-reference.md" in agents
        assert (tmp_path / "docs" / "methodology.md").exists()
        assert (tmp_path / "docs" / "architecture.md").exists()
        assert (tmp_path / "docs" / "adoption-guide.md").exists()
        assert (tmp_path / "docs" / "rules-reference.md").exists()

    def test_full_mode_creates_doc_stubs(self, tmp_path: Path) -> None:
        args = MagicMock()
        args.root = str(tmp_path)
        args.force = False
        args.full = True
        cmd_init(args)

        assert (tmp_path / "docs" / "methodology.md").exists()
        assert (tmp_path / "docs" / "architecture.md").exists()
        assert (tmp_path / "docs" / "adoption-guide.md").exists()
        assert (tmp_path / "docs" / "rules-reference.md").exists()

        # Stubs should have correct frontmatter
        arch = (tmp_path / "docs" / "architecture.md").read_text()
        assert "type: snapshot" in arch
        assert "TODO" in arch

    def test_force_overwrites_existing(self, tmp_path: Path) -> None:
        args = MagicMock()
        args.root = str(tmp_path)
        args.force = False
        args.full = False
        cmd_init(args)

        # Modify a file
        (tmp_path / "AGENTS.md").write_text("old content")

        # Without force, should skip
        args2 = MagicMock()
        args2.root = str(tmp_path)
        args2.force = False
        args2.full = False
        import io
        import sys

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            cmd_init(args2)
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        assert "Skipped" in output
        assert (tmp_path / "AGENTS.md").read_text() == "old content"

        # With force, should overwrite
        args3 = MagicMock()
        args3.root = str(tmp_path)
        args3.force = True
        args3.full = False
        cmd_init(args3)
        assert "old content" not in (tmp_path / "AGENTS.md").read_text()

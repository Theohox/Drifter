"""Tests for ghost reference check."""

from pathlib import Path

from drifter.checks.ghost_reference import GhostReferenceCheck, _get_valid_commands
from drifter.config import Config


class TestGhostReferenceCheck:
    def test_no_issues_when_manifest_matches(self, tmp_path: Path) -> None:
        manifest_dir = tmp_path / ".drifter"
        manifest_dir.mkdir()
        manifest = manifest_dir / "capability-manifest.json"
        manifest.write_text(
            '{"version": "1.0", "commands": [{"name": "check"}], "mcp_tools": []}'
        )
        readme = tmp_path / "README.md"
        readme.write_text("Run `drifter check` to validate.\n")
        config = Config.load(root=tmp_path)
        check = GhostReferenceCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_finds_ghost_command_reference(self, tmp_path: Path) -> None:
        manifest_dir = tmp_path / ".drifter"
        manifest_dir.mkdir()
        manifest = manifest_dir / "capability-manifest.json"
        manifest.write_text(
            '{"version": "1.0", "commands": [{"name": "check"}], "mcp_tools": []}'
        )
        readme = tmp_path / "README.md"
        readme.write_text("Run `drifter ghost` to scan.\n")
        config = Config.load(root=tmp_path)
        check = GhostReferenceCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "ghost" in issues[0].detail

    def test_finds_ghost_mcp_tool_reference(self, tmp_path: Path) -> None:
        manifest_dir = tmp_path / ".drifter"
        manifest_dir.mkdir()
        manifest = manifest_dir / "capability-manifest.json"
        manifest.write_text(
            '{"version": "1.0", "commands": [], "mcp_tools": [{"name": "drifter_check"}]}'
        )
        readme = tmp_path / "README.md"
        readme.write_text("Use drifter_foo to scan.\n")
        config = Config.load(root=tmp_path)
        check = GhostReferenceCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "drifter_foo" in issues[0].detail

    def test_ignores_ignored_paths(self, tmp_path: Path) -> None:
        manifest_dir = tmp_path / ".drifter"
        manifest_dir.mkdir()
        manifest = manifest_dir / "capability-manifest.json"
        manifest.write_text(
            '{"version": "1.0", "commands": [{"name": "check"}], "mcp_tools": []}'
        )
        docs = tmp_path / "docs"
        docs.mkdir()
        readme = docs / "README.md"
        readme.write_text("Run `drifter ghost` to scan.\n")

        # Write config that ignores docs/
        config_file = tmp_path / "drifter.toml"
        config_file.write_text(
            "[drifter]\n"
            "[[drifter.checks]]\n"
            'name = "ghost_reference"\n'
            'ignore_paths = ["docs/*"]\n'
        )
        config = Config.load(root=tmp_path)
        check = GhostReferenceCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_dedupes_repeated_reference_with_line_number(self, tmp_path: Path) -> None:
        manifest_dir = tmp_path / ".drifter"
        manifest_dir.mkdir()
        (manifest_dir / "capability-manifest.json").write_text(
            '{"version": "1.0", "commands": [{"name": "check"}], "mcp_tools": []}'
        )
        readme = tmp_path / "README.md"
        readme.write_text(
            "Intro.\nRun `drifter ghost` here.\nMore text.\nOr `drifter ghost` there.\n"
        )
        config = Config.load(root=tmp_path)
        issues = GhostReferenceCheck().run(tmp_path, config)
        assert len(issues) == 1
        assert "line 2" in issues[0].detail

    def test_adopter_project_with_empty_manifest_commands(self, tmp_path: Path) -> None:
        """Adopting projects have no cli.py, so their manifest lists no commands;
        real Drifter commands in their docs must not be flagged."""
        manifest_dir = tmp_path / ".drifter"
        manifest_dir.mkdir()
        manifest = manifest_dir / "capability-manifest.json"
        manifest.write_text('{"version": "1.0", "commands": [], "mcp_tools": []}')
        readme = tmp_path / "README.md"
        readme.write_text(
            "Run `drifter check` to validate. Never run `drifter frobnicate`.\n"
        )
        config = Config.load(root=tmp_path)
        check = GhostReferenceCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "frobnicate" in issues[0].detail

    def test_skips_draft_documents(self, tmp_path: Path) -> None:
        manifest_dir = tmp_path / ".drifter"
        manifest_dir.mkdir()
        (manifest_dir / "capability-manifest.json").write_text(
            '{"version": "1.0", "commands": [{"name": "check"}], "mcp_tools": []}'
        )
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "sow.md").write_text(
            "---\nstatus: draft\n---\n\nProposed: `drifter truth` audit.\n"
        )
        config = Config.load(root=tmp_path)
        issues = GhostReferenceCheck().run(tmp_path, config)
        assert len(issues) == 0

    def test_skips_archive_documents(self, tmp_path: Path) -> None:
        manifest_dir = tmp_path / ".drifter"
        manifest_dir.mkdir()
        (manifest_dir / "capability-manifest.json").write_text(
            '{"version": "1.0", "commands": [{"name": "check"}], "mcp_tools": []}'
        )
        archive = tmp_path / "docs" / "archive"
        archive.mkdir(parents=True)
        (archive / "old.md").write_text("Run `drifter ghost` to scan.\n")
        config = Config.load(root=tmp_path)
        issues = GhostReferenceCheck().run(tmp_path, config)
        assert len(issues) == 0


class TestGetValidCommands:
    def test_extracts_command_names(self) -> None:
        manifest = {
            "commands": [
                {"name": "check"},
                {"name": "init"},
            ]
        }
        assert _get_valid_commands(manifest) == {"check", "init"}

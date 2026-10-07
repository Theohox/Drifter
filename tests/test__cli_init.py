"""Tests for _cli_init command handlers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import drifter._cli_init as cli_init_mod
from drifter._cli_init import _doc_stub, cmd_init, cmd_validate


class TestDocStub:
    def test_stub_has_frontmatter(self) -> None:
        stub = _doc_stub("Title", "guide", "0", "2026-01-01T00:00:00Z")
        assert stub.startswith("---")
        assert "type: guide" in stub
        assert "title: Title" in stub


class TestCmdValidate:
    def test_empty_project_valid(self, tmp_path: Path, capsys) -> None:
        rc = cmd_validate(SimpleNamespace(root=tmp_path))
        out = capsys.readouterr().out
        assert "DOCUMENT VALIDATION" in out
        assert rc == 0


def _init_args(root: Path, full: bool = False, force: bool = False) -> SimpleNamespace:
    return SimpleNamespace(root=root, full=full, force=force)


class TestCmdInit:
    CORE_FILES: ClassVar = [
        "AGENTS.md",
        "dangerous_patterns.toml",
        "drifter.toml",
        "docs/session-protocol.md",
        "docs/project-conductor.md",
        "docs/digests/index.md",
        "docs/archive/README.md",
    ]
    STUB_FILES: ClassVar = [
        "docs/methodology.md",
        "docs/architecture.md",
        "docs/adoption-guide.md",
        "docs/rules-reference.md",
    ]

    def test_minimal_creates_core_files_only(self, tmp_path: Path, capsys) -> None:
        rc = cmd_init(_init_args(tmp_path, full=False))
        assert rc == 0
        for rel in self.CORE_FILES:
            assert (tmp_path / rel).is_file(), f"{rel} not created"
        for rel in self.STUB_FILES:
            assert not (tmp_path / rel).exists(), f"{rel} created without --full"
        out = capsys.readouterr().out
        for name in (
            "AGENTS.md",
            "dangerous_patterns.toml",
            "session-protocol.md",
            "project-conductor.md",
        ):
            assert name in out

    def test_minimal_writes_real_template_content(self, tmp_path: Path) -> None:
        rc = cmd_init(_init_args(tmp_path, full=False))
        assert rc == 0
        for rel in self.CORE_FILES:
            text = (tmp_path / rel).read_text(encoding="utf-8")
            assert text.strip(), f"{rel} is empty"
            assert "Template not found" not in text
            assert "{{PROJECT_NAME}}" not in text
            assert "{{NOW}}" not in text
        # dangerous_patterns.toml must be real content, never a stub
        assert "always_block" in (tmp_path / "dangerous_patterns.toml").read_text(
            encoding="utf-8"
        )

    def test_project_name_substituted(self, tmp_path: Path) -> None:
        rc = cmd_init(_init_args(tmp_path))
        assert rc == 0
        assert tmp_path.name in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        toml = (tmp_path / "drifter.toml").read_text(encoding="utf-8")
        assert "{{NOW}}" not in toml
        assert "{{PROJECT_NAME}}" not in toml
        assert tmp_path.name in toml

    def test_full_creates_doc_stubs(self, tmp_path: Path, capsys) -> None:
        rc = cmd_init(_init_args(tmp_path, full=True))
        assert rc == 0
        for rel in self.CORE_FILES + self.STUB_FILES:
            assert (tmp_path / rel).is_file(), f"{rel} not created"
        stub = (tmp_path / "docs" / "methodology.md").read_text(encoding="utf-8")
        assert "type: constitution" in stub
        assert "drifter init --full" in stub
        arch = (tmp_path / "docs" / "architecture.md").read_text(encoding="utf-8")
        assert "type: snapshot" in arch
        assert "TODO" in arch
        out = capsys.readouterr().out
        assert "Mode: full" in out

    def test_full_mode_refs_in_agents_are_not_phantom(self, tmp_path: Path) -> None:
        # --full AGENTS.md references canonical docs; init must create them
        rc = cmd_init(_init_args(tmp_path, full=True))
        assert rc == 0
        agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        for rel in self.STUB_FILES:
            assert rel in agents, f"{rel} not referenced in AGENTS.md"
            assert (tmp_path / rel).is_file(), f"{rel} referenced but not created"

    def test_existing_files_skipped_without_force(self, tmp_path: Path, capsys) -> None:
        assert cmd_init(_init_args(tmp_path)) == 0
        agents = tmp_path / "AGENTS.md"
        agents.write_text("custom content\n", encoding="utf-8")
        rc = cmd_init(_init_args(tmp_path, force=False))
        assert rc == 0
        assert "Skipped" in capsys.readouterr().out
        assert agents.read_text(encoding="utf-8") == "custom content\n"

    def test_force_overwrites(self, tmp_path: Path) -> None:
        assert cmd_init(_init_args(tmp_path)) == 0
        agents = tmp_path / "AGENTS.md"
        agents.write_text("custom content\n", encoding="utf-8")
        rc = cmd_init(_init_args(tmp_path, force=True))
        assert rc == 0
        assert agents.read_text(encoding="utf-8") != "custom content\n"

    def test_missing_templates_hard_error_writes_nothing(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        monkeypatch.setattr(cli_init_mod, "template_text", lambda _name: None)
        rc = cmd_init(_init_args(tmp_path))
        assert rc == 1
        err = capsys.readouterr().err
        assert "AGENTS.md.tmpl" in err
        assert "dangerous_patterns.toml.tmpl" in err
        for rel in self.CORE_FILES:
            assert not (tmp_path / rel).exists(), f"{rel} written despite error"

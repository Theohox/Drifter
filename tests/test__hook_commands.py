"""Tests for git pre-commit hook install/uninstall."""

from __future__ import annotations

import subprocess
from pathlib import Path

from drifter._hook_commands import cmd_install_hook, cmd_uninstall_hook


class Namespace:
    def __init__(self, root: Path | None = None):
        self.root = root


class TestInstallHook:
    def test_installs_hook(self, tmp_path: Path) -> None:
        subprocess.run(
            ["git", "init"], cwd=str(tmp_path), capture_output=True, check=True
        )
        args = Namespace(root=tmp_path)
        assert cmd_install_hook(args) == 0
        hook = tmp_path / ".git" / "hooks" / "pre-commit"
        assert hook.exists()
        assert hook.stat().st_mode & 0o111  # executable
        assert "Drifter pre-commit hook" in hook.read_text()

    def test_fails_if_not_git_repo(self, tmp_path: Path) -> None:
        args = Namespace(root=tmp_path)
        assert cmd_install_hook(args) == 1

    def test_fails_if_hook_already_exists(self, tmp_path: Path) -> None:
        subprocess.run(
            ["git", "init"], cwd=str(tmp_path), capture_output=True, check=True
        )
        hook = tmp_path / ".git" / "hooks" / "pre-commit"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text("#!/bin/sh\necho existing\n")
        args = Namespace(root=tmp_path)
        assert cmd_install_hook(args) == 1


class TestUninstallHook:
    def test_uninstalls_drifter_hook(self, tmp_path: Path) -> None:
        subprocess.run(
            ["git", "init"], cwd=str(tmp_path), capture_output=True, check=True
        )
        args = Namespace(root=tmp_path)
        cmd_install_hook(args)
        assert cmd_uninstall_hook(args) == 0
        hook = tmp_path / ".git" / "hooks" / "pre-commit"
        assert not hook.exists()

    def test_succeeds_if_no_hook(self, tmp_path: Path) -> None:
        subprocess.run(
            ["git", "init"], cwd=str(tmp_path), capture_output=True, check=True
        )
        args = Namespace(root=tmp_path)
        assert cmd_uninstall_hook(args) == 0

    def test_refuses_to_remove_foreign_hook(self, tmp_path: Path) -> None:
        subprocess.run(
            ["git", "init"], cwd=str(tmp_path), capture_output=True, check=True
        )
        hook = tmp_path / ".git" / "hooks" / "pre-commit"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text("#!/bin/sh\necho foreign\n")
        args = Namespace(root=tmp_path)
        assert cmd_uninstall_hook(args) == 1
        assert hook.exists()

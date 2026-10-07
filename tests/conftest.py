"""Shared fixtures: tmp-project scaffolds used across multiple test modules."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, check=True)


class GitRepo:
    """A git-initialized tmp project with a commit helper."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def commit(self, message: str, filename: str = "file.txt") -> None:
        (self.path / filename).write_text(f"{message}\n")
        _git(self.path, "add", ".")
        _git(self.path, "commit", "-m", message)


@pytest.fixture
def git_repo(tmp_path: Path) -> GitRepo:
    """git init + user config + initial commit; use .commit(msg) for more."""
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@test.com")
    _git(tmp_path, "config", "user.name", "Test")
    repo = GitRepo(tmp_path)
    repo.commit("initial")
    return repo


@pytest.fixture
def fake_project(tmp_path: Path) -> Callable[[str], Path]:
    """Scaffold a minimal project for the manifest generator.

    Creates pyproject.toml, src/drifter/cli.py, checks/, reporters/, and
    plugins/mcp-server/. Returns a factory so tests can pick the version.
    """

    def _make(version: str = "0.1.0") -> Path:
        (tmp_path / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n')
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        (src / "cli.py").write_text('subparsers.add_parser("check")\n')
        checks = src / "checks"
        checks.mkdir()
        (checks / "__init__.py").write_text("BUILTIN_CHECKS = {}\n")
        mcp = tmp_path / "plugins" / "mcp-server"
        mcp.mkdir(parents=True)
        (mcp / "server.py").write_text("")
        reps = src / "reporters"
        reps.mkdir()
        (reps / "__init__.py").write_text("")
        return tmp_path

    return _make


@pytest.fixture
def minimal_project(tmp_path: Path) -> Callable[..., Path]:
    """Scaffold src/drifter (cli.py + __init__.py) plus optional AGENTS.md/README.md."""

    def _make(
        cli: str = "subparsers.add_parser('check')\n",
        agents: str | None = None,
        readme: str | None = None,
    ) -> Path:
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("")
        (src / "cli.py").write_text(cli)
        if agents is not None:
            (tmp_path / "AGENTS.md").write_text(agents)
        if readme is not None:
            (tmp_path / "README.md").write_text(readme)
        return tmp_path

    return _make


_CONDUCTOR_BASE = (
    "---\ntype: backlog\n---\n"
    "## Current Phase\n**Phase 1** 🟢 ACTIVE\n"
    "## Active Task\n| ID | Name |\n| 1 | Task |\n"
)


@pytest.fixture
def pre_flight_project(tmp_path: Path) -> Callable[..., Path]:
    """Scaffold the pre-flight quartet: AGENTS.md, session protocol, conductor, patterns."""

    def _make(with_patterns: bool = True, conductor_tail: str = "") -> Path:
        (tmp_path / "AGENTS.md").write_text("# AGENTS\n")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "session-protocol.md").write_text("---\ntype: playbook\n---\n")
        (docs / "project-conductor.md").write_text(_CONDUCTOR_BASE + conductor_tail)
        if with_patterns:
            (tmp_path / "dangerous_patterns.toml").write_text(
                "[git]\nalways_block = []\n"
            )
        return tmp_path

    return _make

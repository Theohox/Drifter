"""Tests for the drift guard engine."""

from pathlib import Path

import pytest

from drifter.checks import BUILTIN_CHECKS
from drifter.checks._base import Issue
from drifter.config import Config
from drifter.drift_guard import run_checks


class TestRunChecks:
    def test_empty_project(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        conductor = docs / "project-conductor.md"
        conductor.write_text("""
---
title: Conductor
type: backlog
---
## Current Phase
**Phase 1** 🟢 ACTIVE
## Active Task
| ID | Name |
| 1 | Task |
""")
        patterns = tmp_path / "dangerous_patterns.toml"
        patterns.write_text(
            '[git]\nalways_block = ["git commit"]\n[shell]\nblocked = []\n'
        )
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            "# AGENTS.md\n\nRead dangerous_patterns.toml before running commands.\n"
        )
        readme = tmp_path / "README.md"
        readme.write_text(
            "# Project\n"
            "AGENTS.md dangerous_patterns.toml session-protocol.md project-conductor.md\n"
            "drifter check drifter preflight drifter conductor "
            "drifter validate drifter audit drifter init\n"
            "enforcement dangerous_patterns session audit pre-flight conductor\n"
        )
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".env\n")
        report = run_checks(root=tmp_path, config=config)
        assert report.score == 100
        assert report.total == 0


class FakeMixedCheck:
    """Fake check emitting one error and one warn, for severity-ceiling tests."""

    name = "fake_mixed"

    def run(self, root: Path, config: Config) -> list[Issue]:
        return [
            Issue(check=self.name, file="a.py", detail="bad", severity="error"),
            Issue(check=self.name, file="b.py", detail="meh", severity="warn"),
        ]


class TestSeverityCeiling:
    @staticmethod
    def _config_for_fake(tmp_path: Path, severity: str) -> Config:
        config = Config.load(
            root=tmp_path,
            overrides={
                "checks": [
                    {"name": "fake_mixed", "enabled": True, "severity": severity}
                ]
            },
        )
        for c in config.checks:
            if c.name != "fake_mixed":
                c.enabled = False
        return config

    def test_configured_severity_demotes_issues(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(BUILTIN_CHECKS, "fake_mixed", FakeMixedCheck)
        config = self._config_for_fake(tmp_path, "warn")
        report = run_checks(root=tmp_path, config=config)
        assert report.errors == 0
        assert report.warns == 2
        assert report.score == 96

    def test_ceiling_never_escalates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(BUILTIN_CHECKS, "fake_mixed", FakeMixedCheck)
        config = self._config_for_fake(tmp_path, "error")
        report = run_checks(root=tmp_path, config=config)
        assert report.errors == 1
        assert report.warns == 1

    def test_info_ceiling_flattens_all(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(BUILTIN_CHECKS, "fake_mixed", FakeMixedCheck)
        config = self._config_for_fake(tmp_path, "info")
        report = run_checks(root=tmp_path, config=config)
        assert report.errors == 0
        assert report.warns == 0
        assert report.infos == 2


CUSTOM_CHECK = """
from pathlib import Path

from drifter.checks._base import Issue


class AlwaysFlagCheck:
    name = "always_flag"

    def run(self, root: Path, config) -> list:
        return [
            Issue(check=self.name, file="x.py", detail="flagged", severity="error")
        ]
"""


class TestCustomChecks:
    @staticmethod
    def _write_check(tmp_path: Path, content: str = CUSTOM_CHECK) -> Path:
        check_file = tmp_path / "my_checks" / "always_flag.py"
        check_file.parent.mkdir(parents=True, exist_ok=True)
        check_file.write_text(content)
        return check_file

    @staticmethod
    def _config(tmp_path: Path, entry: dict) -> Config:
        config = Config.load(root=tmp_path, overrides={"checks": [entry]})
        for c in config.checks:
            if c.name != entry["name"]:
                c.enabled = False
        return config

    def test_loads_and_runs_custom_check(self, tmp_path: Path) -> None:
        self._write_check(tmp_path)
        config = self._config(
            tmp_path, {"name": "always_flag", "path": "my_checks/always_flag.py"}
        )
        report = run_checks(root=tmp_path, config=config)
        flagged = [i for i in report.issues if i.check == "always_flag"]
        assert len(flagged) == 1
        assert flagged[0].detail == "flagged"

    def test_custom_check_respects_severity_ceiling(self, tmp_path: Path) -> None:
        self._write_check(tmp_path)
        config = self._config(
            tmp_path,
            {
                "name": "always_flag",
                "path": "my_checks/always_flag.py",
                "severity": "warn",
            },
        )
        report = run_checks(root=tmp_path, config=config)
        flagged = [i for i in report.issues if i.check == "always_flag"]
        assert len(flagged) == 1
        assert flagged[0].severity == "warn"
        assert report.errors == 0

    def test_missing_path_is_error_issue(self, tmp_path: Path) -> None:
        config = self._config(
            tmp_path, {"name": "ghost_check", "path": "my_checks/nope.py"}
        )
        report = run_checks(root=tmp_path, config=config)
        issues = [i for i in report.issues if i.check == "ghost_check"]
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "not found" in issues[0].detail

    def test_module_without_check_class_is_error_issue(self, tmp_path: Path) -> None:
        self._write_check(tmp_path, "X = 1\n")
        config = self._config(
            tmp_path, {"name": "always_flag", "path": "my_checks/always_flag.py"}
        )
        report = run_checks(root=tmp_path, config=config)
        issues = [i for i in report.issues if i.check == "always_flag"]
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "exactly one check class" in issues[0].detail

    def test_import_error_is_error_issue(self, tmp_path: Path) -> None:
        self._write_check(tmp_path, "def broken(:\n")
        config = self._config(
            tmp_path, {"name": "always_flag", "path": "my_checks/always_flag.py"}
        )
        report = run_checks(root=tmp_path, config=config)
        issues = [i for i in report.issues if i.check == "always_flag"]
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "failed to import" in issues[0].detail

    def test_unknown_check_without_path_warns(self, tmp_path: Path) -> None:
        config = self._config(tmp_path, {"name": "typo_check"})
        report = run_checks(root=tmp_path, config=config)
        issues = [i for i in report.issues if i.check == "typo_check"]
        assert len(issues) == 1
        assert issues[0].severity == "warn"
        assert "no builtin, no path" in issues[0].detail

    def test_builtin_name_collision_builtin_wins(self, tmp_path: Path) -> None:
        self._write_check(tmp_path)
        config = self._config(
            tmp_path,
            {"name": "stale_reference", "path": "my_checks/always_flag.py"},
        )
        report = run_checks(root=tmp_path, config=config)
        collisions = [i for i in report.issues if "collides with a builtin" in i.detail]
        assert len(collisions) == 1
        assert collisions[0].severity == "warn"
        # The custom check class must NOT have run under the builtin's name
        assert not any(i.detail == "flagged" for i in report.issues)

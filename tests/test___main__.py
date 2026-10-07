"""Tests for the module entry point and package version."""

import importlib.metadata
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

import drifter
import drifter.cli

PROJECT_ROOT = Path(__file__).parent.parent


class TestMainEntryPoint:
    def test_module_runs_without_crash(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "drifter", "--help"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()

    def test_module_exit_code_propagates(self, monkeypatch) -> None:
        monkeypatch.setattr(drifter.cli, "main", lambda: 3)
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("drifter.__main__", run_name="__main__")
        assert exc_info.value.code == 3

    def test_check_exit_code_propagates_to_subprocess(self, tmp_path: Path) -> None:
        """`python -m drifter check` exits 1 in a drifting project (sys.exit wiring)."""
        result = subprocess.run(
            [sys.executable, "-m", "drifter", "--root", str(tmp_path), "check"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1
        assert "error" in result.stdout.lower()

    def test_check_score_exit_code_in_subprocess(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "drifter",
                "--root",
                str(tmp_path),
                "check",
                "--score",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        # Empty project drifts -> rc 1 via sys.exit(main())
        assert result.returncode == 1
        assert "SCORE:" in result.stdout


class TestVersion:
    def test_version_matches_distribution(self) -> None:
        try:
            expected = importlib.metadata.version("drifter-check")
        except importlib.metadata.PackageNotFoundError:
            assert drifter.__version__ == "0.0.0+unknown"
        else:
            assert drifter.__version__ == expected

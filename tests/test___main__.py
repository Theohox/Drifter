"""Tests for the module entry point."""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


class TestMainEntryPoint:
    def test_module_runs_without_crash(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "drifter", "--help"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()

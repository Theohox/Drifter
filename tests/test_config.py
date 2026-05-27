"""Tests for configuration loader."""

from pathlib import Path

import pytest

from drifter.config import Config


class TestConfig:
    def test_default_config(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        assert config.root == tmp_path
        assert config.drift_threshold == 70
        assert config.max_pending_age_days == 7
        assert len(config.checks) == 33

    def test_pyproject_override(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.drifter]
drift_threshold = 50
max_pending_age_days = 3
""")
        config = Config.load(root=tmp_path)
        assert config.drift_threshold == 50
        assert config.max_pending_age_days == 3

    def test_drifter_toml_override(self, tmp_path: Path) -> None:
        drifter_toml = tmp_path / "drifter.toml"
        drifter_toml.write_text("""
[drifter]
drift_threshold = 90
""")
        config = Config.load(root=tmp_path)
        assert config.drift_threshold == 90

    def test_is_ignored(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        assert config.is_ignored(tmp_path / "venv" / "foo.py")
        assert not config.is_ignored(tmp_path / "src" / "foo.py")

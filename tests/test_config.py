"""Tests for configuration loader."""

from pathlib import Path


from drifter.config import Config


class TestConfig:
    def test_default_config(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        assert config.root == tmp_path
        assert config.drift_threshold == 70
        assert config.max_pending_age_days == 7
        assert len(config.checks) == 34

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
        assert config.is_ignored(tmp_path / ".venv" / "bin" / "python")
        assert config.is_ignored(tmp_path / "node_modules" / "lodash" / "index.js")
        assert config.is_ignored(
            tmp_path / "src" / "__pycache__" / "foo.cpython-312.pyc"
        )
        assert not config.is_ignored(tmp_path / "src" / "foo.py")
        assert not config.is_ignored(tmp_path / "myvenv" / "foo.py")
        assert not config.is_ignored(tmp_path / "src" / "venv_utils.py")

    def test_check_config_per_check_suppression(self, tmp_path: Path) -> None:
        drifter_toml = tmp_path / "drifter.toml"
        drifter_toml.write_text("""
[drifter.check_config.hardcoded_path]
ignore_paths = ["docs/examples/**"]
ignore_patterns = ["*/fixtures/*"]
""")
        config = Config.load(root=tmp_path)
        cfg = config.check_config("hardcoded_path")
        assert cfg.ignore_paths == ["docs/examples/**"]
        assert cfg.ignore_patterns == ["*/fixtures/*"]

    def test_is_check_ignored(self, tmp_path: Path) -> None:
        drifter_toml = tmp_path / "drifter.toml"
        drifter_toml.write_text("""
[drifter.check_config.hardcoded_path]
ignore_paths = ["docs/examples/**"]
""")
        config = Config.load(root=tmp_path)
        assert config.is_check_ignored(
            "hardcoded_path", tmp_path / "docs" / "examples" / "demo.py"
        )
        assert not config.is_check_ignored(
            "other_check", tmp_path / "docs" / "examples" / "demo.py"
        )

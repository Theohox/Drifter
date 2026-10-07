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
        assert len(config.checks) == 35

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

    def test_sparse_checks_overlay_preserves_defaults(self, tmp_path: Path) -> None:
        """Regression: a sparse drifter.toml must not silently disable checks."""
        drifter_toml = tmp_path / "drifter.toml"
        drifter_toml.write_text("""
[[drifter.checks]]
name = "stale_reference"
enabled = false
""")
        config = Config.load(root=tmp_path)
        assert len(config.checks) == 35
        stale = config.check_config("stale_reference")
        assert stale.enabled is False
        assert stale.severity == "warn"
        assert config.check_config("credential_leak").enabled is True

    def test_check_list_new_name_appended(self, tmp_path: Path) -> None:
        drifter_toml = tmp_path / "drifter.toml"
        drifter_toml.write_text("""
[[drifter.checks]]
name = "my_custom_check"
enabled = true
severity = "error"
""")
        config = Config.load(root=tmp_path)
        assert len(config.checks) == 36
        custom = config.check_config("my_custom_check")
        assert custom.enabled is True
        assert custom.severity == "error"

    def test_explicit_empty_checks_list_disables_suite(self, tmp_path: Path) -> None:
        drifter_toml = tmp_path / "drifter.toml"
        drifter_toml.write_text("""
[drifter]
checks = []
""")
        config = Config.load(root=tmp_path)
        assert config.checks == []

    def test_pyproject_sparse_checks_overlay(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.drifter]
checks = [{name = "no_rush", severity = "info"}]
""")
        config = Config.load(root=tmp_path)
        assert len(config.checks) == 35
        no_rush = config.check_config("no_rush")
        assert no_rush.enabled is True
        assert no_rush.severity == "info"

    def test_layered_sparse_checks_merge_per_name(self, tmp_path: Path) -> None:
        drifter_toml = tmp_path / "drifter.toml"
        drifter_toml.write_text("""
[[drifter.checks]]
name = "stale_reference"
enabled = false
""")
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.drifter]
checks = [{name = "stale_reference", severity = "error"}]
""")
        config = Config.load(root=tmp_path)
        stale = config.check_config("stale_reference")
        assert stale.enabled is False
        assert stale.severity == "error"

    def test_legacy_tool_drifter_section_in_drifter_toml(self, tmp_path: Path) -> None:
        """Backward compat: old configs used [tool.drifter] inside drifter.toml."""
        drifter_toml = tmp_path / "drifter.toml"
        drifter_toml.write_text("""
[tool.drifter]
drift_threshold = 55

[[tool.drifter.checks]]
name = "stale_reference"
enabled = false
""")
        config = Config.load(root=tmp_path)
        assert config.drift_threshold == 55
        assert len(config.checks) == 35
        assert config.check_config("stale_reference").enabled is False
        assert config.check_config("credential_leak").enabled is True

    def test_is_ignored_multi_segment_dir_pattern(self, tmp_path: Path) -> None:
        """Multi-segment directory patterns match relative and absolute paths."""
        drifter_toml = tmp_path / "drifter.toml"
        drifter_toml.write_text("""
[drifter.ignore]
paths = ["frontend/src-tauri/sidecar/"]
""")
        config = Config.load(root=tmp_path)
        rel = Path("frontend/src-tauri/sidecar/pkg/mod.py")
        assert config.is_ignored(rel)
        assert config.is_ignored(
            tmp_path / "frontend" / "src-tauri" / "sidecar" / "pkg" / "mod.py"
        )
        assert not config.is_ignored(Path("frontend/src/main.py"))
        assert not config.is_ignored(Path("other/sidecar/pkg/mod.py"))

    def test_check_path_parsed(self, tmp_path: Path) -> None:
        """Custom check entries may declare a path to load from."""
        drifter_toml = tmp_path / "drifter.toml"
        drifter_toml.write_text("""
[[drifter.checks]]
name = "my_custom_check"
path = "checks/my_custom_check.py"
severity = "error"
""")
        config = Config.load(root=tmp_path)
        custom = config.check_config("my_custom_check")
        assert custom.path == "checks/my_custom_check.py"
        assert custom.severity == "error"
        # Builtins have no path
        assert config.check_config("stale_reference").path is None

    def test_check_config_unknown_name_kept(self, tmp_path: Path) -> None:
        """[drifter.check_config.<name>] for an unknown name is kept, not dropped."""
        drifter_toml = tmp_path / "drifter.toml"
        drifter_toml.write_text("""
[drifter.check_config.my_custom_check]
path = "checks/my_custom_check.py"
""")
        config = Config.load(root=tmp_path)
        custom = config.check_config("my_custom_check")
        assert custom.path == "checks/my_custom_check.py"

    def test_corrupted_toml_warns(self, tmp_path: Path) -> None:
        """A corrupted drifter.toml must warn visibly, not silently fall back."""
        drifter_toml = tmp_path / "drifter.toml"
        drifter_toml.write_text("[drifter\ngarbage =")
        with pytest.warns(UserWarning, match="Could not parse"):
            config = Config.load(root=tmp_path)
        # Falls back to defaults
        assert config.drift_threshold == 70

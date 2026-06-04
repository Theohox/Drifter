"""Tests for config sync check."""

from pathlib import Path

from drifter.config import Config
from drifter.checks.config_sync import ConfigSyncCheck


class TestConfigSyncCheck:
    def test_all_synced_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        # Create manifest with one check
        manifest = tmp_path / "drifter-manifest.toml"
        manifest.write_text('[checks]\ncount = 1\nnames = ["stale_reference"]\n')
        # Create config.py with matching check
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        config_py = src / "config.py"
        config_py.write_text(
            'DEFAULT_CONFIG = {"checks": [{"name": "stale_reference"}]}\n'
        )
        # Create drifter.toml with matching check
        drifter_toml = tmp_path / "drifter.toml"
        drifter_toml.write_text(
            '[drifter]\n[[drifter.checks]]\nname = "stale_reference"\n'
        )
        check = ConfigSyncCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_missing_from_config_py(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        manifest = tmp_path / "drifter-manifest.toml"
        manifest.write_text('[checks]\ncount = 1\nnames = ["stale_reference"]\n')
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        config_py = src / "config.py"
        config_py.write_text('DEFAULT_CONFIG = {"checks": []}\n')
        check = ConfigSyncCheck()
        issues = check.run(tmp_path, config)
        assert any("missing from DEFAULT_CONFIG" in i.detail for i in issues)

    def test_orphan_in_drifter_toml(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        manifest = tmp_path / "drifter-manifest.toml"
        manifest.write_text('[checks]\ncount = 1\nnames = ["stale_reference"]\n')
        drifter_toml = tmp_path / "drifter.toml"
        drifter_toml.write_text('[drifter]\n[[drifter.checks]]\nname = "old_check"\n')
        check = ConfigSyncCheck()
        issues = check.run(tmp_path, config)
        assert any("old_check" in i.detail and "drifter.toml" in i.file for i in issues)

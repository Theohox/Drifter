"""Tests for safe TOML loading."""

from pathlib import Path

from drifter._toml_utils import safe_load_toml


class TestSafeLoadToml:
    def test_loads_valid_toml(self, tmp_path: Path) -> None:
        path = tmp_path / "valid.toml"
        path.write_text("[section]\nkey = 'value'\n", encoding="utf-8")
        result = safe_load_toml(path)
        assert result == {"section": {"key": "value"}}

    def test_returns_none_on_corrupted_toml(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.toml"
        path.write_text("[section\nkey = 'value'\n", encoding="utf-8")
        result = safe_load_toml(path)
        assert result is None

    def test_returns_none_on_missing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.toml"
        result = safe_load_toml(path)
        assert result is None

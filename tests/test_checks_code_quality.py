"""Tests for code quality checks (checks/code_quality.py)."""

from pathlib import Path

from drifter.checks.code_quality import TomllibCompatibilityCheck
from drifter.config import Config


class TestTomllibCompatibilityCheck:
    def test_detects_bare_tomllib(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "drifter" / "foo.py"
        src.parent.mkdir(parents=True)
        src.write_text("import tomllib\n")
        check = TomllibCompatibilityCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 1
        assert "bare 'import tomllib'" in issues[0].detail

    def test_allows_guarded_tomllib(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        src = tmp_path / "src" / "drifter" / "foo.py"
        src.parent.mkdir(parents=True)
        src.write_text(
            "import sys\n"
            "if sys.version_info >= (3, 11):\n"
            "    import tomllib\n"
            "else:\n"
            "    import tomli as tomllib\n"
        )
        check = TomllibCompatibilityCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

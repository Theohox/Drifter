"""Tests for MCP server tools.

fastmcp is an optional dependency; these tests mock it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock


# Mock fastmcp before importing the server
_fake_fastmcp = MagicMock()
_fake_fastmcp.FastMCP = lambda name: MagicMock(tool=lambda: lambda f: f)
sys.modules["fastmcp"] = _fake_fastmcp

# Add src and plugins to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "plugins/mcp-server"))

from server import (  # noqa: E402
    _require_auth,
    drifter_check,
    drifter_classify,
    drifter_enforce,
    drifter_log,
    drifter_preflight,
)


class TestMcpAuth:
    def test_no_token_required_by_default(self) -> None:
        assert _require_auth("") is None
        assert _require_auth("wrong") is None

    def test_invalid_token_rejected(self) -> None:
        import server as _server

        original = _server._EXPECTED_TOKEN
        try:
            _server._EXPECTED_TOKEN = "secret123"
            assert _server._require_auth("wrong") is not None
            assert _server._require_auth("") is not None
            assert _server._require_auth("secret123") is None
        finally:
            _server._EXPECTED_TOKEN = original

    def test_classify_rejects_bad_token(self, tmp_path: Path) -> None:
        import server as _server

        original = _server._EXPECTED_TOKEN
        try:
            _server._EXPECTED_TOKEN = "secret123"
            result = json.loads(
                _server.drifter_classify("git status", root=str(tmp_path), token="bad")
            )
            assert result["status"] == "error"
        finally:
            _server._EXPECTED_TOKEN = original


class TestDrifterClassify:
    def test_classifies_safe_command(self, tmp_path: Path) -> None:
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text(
            '[git]\nalways_block = ["git commit"]\n[shell]\nblocked = ["rm -rf /"]\n'
        )
        result = json.loads(drifter_classify("git status", root=str(tmp_path)))
        assert result["action"] == "allow"

    def test_classifies_blocked_command(self, tmp_path: Path) -> None:
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text('[git]\nalways_block = ["git commit"]\n')
        result = json.loads(drifter_classify("git commit -m test", root=str(tmp_path)))
        assert result["action"] == "block"

    def test_invalid_root(self, tmp_path: Path) -> None:
        bad_root = tmp_path / "nonexistent"
        # Should not crash; ShellGuard handles missing patterns gracefully
        result = json.loads(drifter_classify("echo hello", root=str(bad_root)))
        assert "action" in result


class TestDrifterEnforce:
    def test_allows_safe_command(self, tmp_path: Path) -> None:
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text('[git]\nalways_block = ["git commit"]\n')
        result = json.loads(drifter_enforce("git status", root=str(tmp_path)))
        assert result["status"] == "allowed"

    def test_blocks_dangerous_command(self, tmp_path: Path) -> None:
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text('[git]\nalways_block = ["git commit"]\n')
        result = json.loads(drifter_enforce("git commit -m test", root=str(tmp_path)))
        assert result["status"] == "blocked"
        assert "git commit" in result["command"]

    def test_approval_required(self, tmp_path: Path) -> None:
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text('[git]\napproval_required = ["git add"]\n')
        result = json.loads(drifter_enforce("git add file.txt", root=str(tmp_path)))
        assert result["status"] == "approval_required"


class TestDrifterLog:
    def test_logs_action(self, tmp_path: Path) -> None:
        result = json.loads(drifter_log("READ", "test.py", root=str(tmp_path)))
        assert result["status"] == "logged"
        assert result["action"] == "READ"
        assert result["target"] == "test.py"


class TestDrifterPreflight:
    def test_runs_preflight(self, tmp_path: Path) -> None:
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text('[git]\nalways_block = ["git commit"]\n')
        result = json.loads(drifter_preflight(root=str(tmp_path)))
        assert "passed" in result
        assert "drift_score" in result
        assert isinstance(result["step_results"], list)

    def test_with_keyword(self, tmp_path: Path) -> None:
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text('[git]\nalways_block = ["git commit"]\n')
        result = json.loads(
            drifter_preflight(task="test", keyword="TODO", root=str(tmp_path))
        )
        assert "passed" in result


class TestDrifterCheck:
    def test_runs_checks(self, tmp_path: Path) -> None:
        dp = tmp_path / "dangerous_patterns.toml"
        dp.write_text('[git]\nalways_block = ["git commit"]\n')
        result = json.loads(drifter_check(root=str(tmp_path)))
        assert "score" in result
        assert "total" in result
        assert isinstance(result["errors"], int)
        assert isinstance(result["warns"], int)

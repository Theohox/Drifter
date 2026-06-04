"""MCP server for Drifter — wraps enforcement primitives as MCP tools.

This server exposes Drifter's core enforcement (shell guard, session logging,
pre-flight) as Model Context Protocol (MCP) tools. It is a consumer of the
core library, not the enforcement layer itself.

Dependencies:
    pip install fastmcp

Run:
    python plugins/mcp-server/server.py
"""

from __future__ import annotations

import hmac
import json
import os
import sys
from pathlib import Path

# Ensure core drifter is importable
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from drifter.errors import ApprovalRequiredError, DangerousCommandError
from drifter.plugin_api import ToolInterceptor
from drifter.session_logger import SessionLogger
from drifter.shell_guard import ShellGuard


try:
    from fastmcp import FastMCP
except ImportError as exc:
    raise SystemExit(
        "fastmcp is required for the MCP server. "
        "Install it with: pip install fastmcp"
    ) from exc


mcp = FastMCP("drifter")

_EXPECTED_TOKEN = os.environ.get("DRIFTER_MCP_TOKEN")


def _require_auth(token: str) -> dict | None:
    """Return error dict if token is required but invalid."""
    if _EXPECTED_TOKEN:
        if not hmac.compare_digest(_EXPECTED_TOKEN, token):
            return {"status": "error", "reason": "Invalid authentication token"}
    return None


@mcp.tool()
def drifter_classify(command: str, root: str = ".", token: str = "") -> str:
    auth_error = _require_auth(token)
    if auth_error:
        return json.dumps(auth_error)
    """Classify a shell command via Drifter's ShellGuard.

    Returns: JSON with action, reason, matched_pattern.
    """
    guard = ShellGuard(root=Path(root))
    classification = guard.classify(command)
    return json.dumps({
        "action": classification.action,
        "reason": classification.reason,
        "matched_pattern": classification.matched_pattern,
    })


@mcp.tool()
def drifter_enforce(command: str, root: str = ".", token: str = "") -> str:
    auth_error = _require_auth(token)
    if auth_error:
        return json.dumps(auth_error)
    """Enforce a shell command via Drifter's ShellGuard.

    Raises DangerousCommandError or ApprovalRequiredError on violation.
    Returns: JSON with action on success.
    """
    interceptor = ToolInterceptor(root=Path(root))
    try:
        classification = interceptor.before_shell(command)
        return json.dumps({
            "action": classification.action,
            "reason": classification.reason,
            "matched_pattern": classification.matched_pattern,
            "status": "allowed",
        })
    except DangerousCommandError as e:
        return json.dumps({
            "status": "blocked",
            "command": e.command,
            "pattern": e.pattern,
            "reason": str(e),
        })
    except ApprovalRequiredError as e:
        return json.dumps({
            "status": "approval_required",
            "command": e.command,
            "reason": str(e),
        })


@mcp.tool()
def drifter_log(action: str, target: str, root: str = ".", token: str = "") -> str:
    auth_error = _require_auth(token)
    if auth_error:
        return json.dumps(auth_error)
    """Log an action to the Drifter session audit log."""
    logger = SessionLogger(root=Path(root))
    logger.log(action, target)
    return json.dumps({"status": "logged", "action": action, "target": target})


@mcp.tool()
def drifter_preflight(task: str | None = None, keyword: str | None = None, root: str = ".", token: str = "") -> str:
    auth_error = _require_auth(token)
    if auth_error:
        return json.dumps(auth_error)
    """Run the Drifter pre-flight checklist.

    Returns: JSON with passed, drift_score, errors, step_results.
    """
    from drifter.config import Config
    from drifter.pre_flight import run_pre_flight

    path_root = Path(root)
    config = Config.load(root=path_root)
    result = run_pre_flight(root=path_root, config=config, task=task, keyword=keyword)
    return json.dumps({
        "passed": result.passed,
        "drift_score": result.drift_score,
        "errors": result.errors,
        "step_results": result.step_results,
    })


@mcp.tool()
def drifter_check(root: str = ".", token: str = "") -> str:
    auth_error = _require_auth(token)
    if auth_error:
        return json.dumps(auth_error)
    """Run the Drifter drift guard.

    Returns: JSON with score, errors, warns, total.
    """
    from drifter.config import Config
    from drifter.drift_guard import run_checks

    path_root = Path(root)
    config = Config.load(root=path_root)
    report = run_checks(root=path_root, config=config)
    return json.dumps({
        "score": report.score,
        "total": report.total,
        "errors": report.errors,
        "warns": report.warns,
        "infos": report.infos,
    })


if __name__ == "__main__":
    mcp.run()

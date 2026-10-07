"""MCP server for Drifter — wraps enforcement primitives as MCP tools.

This server exposes Drifter's core enforcement (shell guard, session logging,
pre-flight) as Model Context Protocol (MCP) tools. It is a consumer of the
core library, not the enforcement layer itself.

Dependencies:
    pip install "drifter-check[mcp]"

Run:
    python plugins/mcp-server/server.py

Root resolution:
    Each tool accepts an optional `root` argument. If omitted, the
    DRIFTER_ROOT environment variable is used; if that is also unset,
    the current working directory is used.
"""

from __future__ import annotations

import hmac
import json
import os
import sys
from pathlib import Path

# Ensure core drifter is importable when running from a source checkout
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from drifter.config import Config  # noqa: E402
from drifter.drift_guard import run_checks  # noqa: E402
from drifter.errors import ApprovalRequiredError, DangerousCommandError  # noqa: E402
from drifter.plugin_api import ToolInterceptor  # noqa: E402
from drifter.pre_flight import run_pre_flight  # noqa: E402
from drifter.session_logger import SessionLogger  # noqa: E402
from drifter.shell_guard import ShellGuard  # noqa: E402


try:
    from fastmcp import FastMCP
except ImportError as exc:
    raise SystemExit(
        "fastmcp is required for the MCP server. "
        'Install it with: pip install "drifter-check[mcp]"'
    ) from exc


mcp = FastMCP("drifter")

_EXPECTED_TOKEN = os.environ.get("DRIFTER_MCP_TOKEN")


def _require_auth(token: str) -> dict | None:
    """Return error dict if token is required but invalid."""
    if _EXPECTED_TOKEN:
        if not hmac.compare_digest(_EXPECTED_TOKEN, token):
            return {"status": "error", "reason": "Invalid authentication token"}
    return None


def _resolve_root(root: str | None) -> Path:
    """Resolve the project root for a tool call.

    Precedence: explicit `root` argument > DRIFTER_ROOT env var > current
    working directory.
    """
    if root:
        return Path(root)
    return Path(os.environ.get("DRIFTER_ROOT", "."))


def mcp_tool(**kwargs):
    """Register a function as an MCP tool via the underlying @mcp.tool()."""

    def decorator(f):
        return mcp.tool(**kwargs)(f)

    return decorator


@mcp_tool()
def drifter_classify(command: str, root: str | None = None, token: str = "") -> str:
    """Classify a shell command via Drifter's ShellGuard.

    Returns: JSON with action, reason, matched_pattern.
    """
    auth_error = _require_auth(token)
    if auth_error:
        return json.dumps(auth_error)
    guard = ShellGuard(root=_resolve_root(root))
    classification = guard.classify(command)
    return json.dumps(
        {
            "action": classification.action,
            "reason": classification.reason,
            "matched_pattern": classification.matched_pattern,
        }
    )


@mcp_tool()
def drifter_enforce(command: str, root: str | None = None, token: str = "") -> str:
    """Enforce a shell command via Drifter's ShellGuard.

    Never raises; returns JSON with status "allowed", "blocked", or
    "approval_required" (plus action/reason/matched_pattern when allowed).
    """
    auth_error = _require_auth(token)
    if auth_error:
        return json.dumps(auth_error)
    interceptor = ToolInterceptor(root=_resolve_root(root))
    try:
        classification = interceptor.before_shell(command)
        return json.dumps(
            {
                "action": classification.action,
                "reason": classification.reason,
                "matched_pattern": classification.matched_pattern,
                "status": "allowed",
            }
        )
    except DangerousCommandError as e:
        return json.dumps(
            {
                "status": "blocked",
                "command": e.command,
                "pattern": e.pattern,
                "reason": str(e),
            }
        )
    except ApprovalRequiredError as e:
        return json.dumps(
            {
                "status": "approval_required",
                "command": e.command,
                "reason": str(e),
            }
        )


@mcp_tool()
def drifter_log(
    action: str, target: str, root: str | None = None, token: str = ""
) -> str:
    """Log an action to the Drifter session audit log."""
    auth_error = _require_auth(token)
    if auth_error:
        return json.dumps(auth_error)
    logger = SessionLogger(root=_resolve_root(root))
    logger.log(action, target)
    return json.dumps({"status": "logged", "action": action, "target": target})


@mcp_tool()
def drifter_preflight(
    task: str | None = None,
    keyword: str | None = None,
    root: str | None = None,
    token: str = "",
) -> str:
    """Run the Drifter pre-flight checklist.

    Returns: JSON with passed, drift_score, errors, step_results.
    """
    auth_error = _require_auth(token)
    if auth_error:
        return json.dumps(auth_error)
    path_root = _resolve_root(root)
    config = Config.load(root=path_root)
    result = run_pre_flight(root=path_root, config=config, task=task, keyword=keyword)
    return json.dumps(
        {
            "passed": result.passed,
            "drift_score": result.drift_score,
            "errors": result.errors,
            "step_results": result.step_results,
        }
    )


@mcp_tool()
def drifter_check(root: str | None = None, token: str = "") -> str:
    """Run the Drifter drift guard.

    Returns: JSON with score, errors, warns, total.
    """
    auth_error = _require_auth(token)
    if auth_error:
        return json.dumps(auth_error)
    path_root = _resolve_root(root)
    config = Config.load(root=path_root)
    report = run_checks(root=path_root, config=config)
    return json.dumps(
        {
            "score": report.score,
            "total": report.total,
            "errors": report.errors,
            "warns": report.warns,
            "infos": report.infos,
        }
    )


if __name__ == "__main__":
    mcp.run()

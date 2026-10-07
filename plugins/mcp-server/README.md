---
title: Drifter MCP Server
type: guide
version: "1.0"
status: active
phase: "3"
created: '2026-06-01T16:15:00Z'
updated: '2026-10-07T00:00:00Z'
---

# Drifter MCP Server

MCP (Model Context Protocol) server that exposes Drifter's enforcement primitives as tools for any MCP-compatible agent.

**This plugin ships in the Drifter repository, not in the `drifter-check` wheel.** To run it, either run `server.py` from a Drifter source checkout (it adds `src/` to `sys.path` automatically) or copy `server.py` into your own project with `drifter-check` installed.

## Tools

| Tool | Purpose |
|------|---------|
| `drifter_classify` | Classify a shell command without enforcing. Returns action, reason, matched pattern. |
| `drifter_enforce` | Enforce a shell command. Returns `allowed`, `blocked`, or `approval_required`. |
| `drifter_log` | Log an action (READ/WRITE/SHELL/CHECK) to the session audit log. |
| `drifter_preflight` | Run the 7-step pre-flight checklist. Returns pass/fail + drift score. |
| `drifter_check` | Run the full drift guard. Returns score, errors, warns, total. |

## Installation

```bash
# Install Drifter + MCP dependencies from GitHub (PyPI publish pending)
pip install "drifter-check[mcp] @ git+https://github.com/Theohox/Drifter.git"

# Or install in development mode
cd /path/to/drifter
pip install -e ".[dev,mcp]"
```

## Running

```bash
# Start the MCP server
python plugins/mcp-server/server.py

# Or with a specific root
DRIFTER_ROOT=/path/to/project python plugins/mcp-server/server.py
```

## Configuration

The server reads `dangerous_patterns.toml` and `drifter.toml` from the project root.

Project root resolution, in order of precedence:

1. The per-call `root` argument passed to a tool (always wins).
2. The `DRIFTER_ROOT` environment variable.
3. The current working directory.

## Error Handling

- **Missing `dangerous_patterns.toml`**: `drifter_classify` and `drifter_enforce` return `allow` for all commands.
- **Blocked commands**: `drifter_enforce` returns JSON with `status: "blocked"` instead of raising.
- **Approval required**: `drifter_enforce` returns JSON with `status: "approval_required"`.

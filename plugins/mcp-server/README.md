---
title: Drifter MCP Server
type: guide
version: "1.0"
status: active
phase: "3"
created: '2026-06-01T16:15:00Z'
updated: '2026-06-01T16:15:00Z'
---

# Drifter MCP Server

MCP (Model Context Protocol) server that exposes Drifter's enforcement primitives as tools for any MCP-compatible agent.

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
# Install Drifter + MCP dependencies
pip install drifter fastmcp

# Or install in development mode
cd /path/to/drifter
pip install -e ".[dev]"
pip install fastmcp
```

## Running

```bash
# Start the MCP server
python plugins/mcp-server/server.py

# Or with a specific root
DRIFTER_ROOT=/path/to/project python plugins/mcp-server/server.py
```

## Configuration

The server reads `dangerous_patterns.toml` and `drifter.toml` from the project root (default: current directory).

Set `DRIFTER_ROOT` environment variable to point to a specific project.

## Error Handling

- **Missing `dangerous_patterns.toml`**: `drifter_classify` and `drifter_enforce` return `allow` for all commands.
- **Blocked commands**: `drifter_enforce` returns JSON with `status: "blocked"` instead of raising.
- **Approval required**: `drifter_enforce` returns JSON with `status: "approval_required"`.

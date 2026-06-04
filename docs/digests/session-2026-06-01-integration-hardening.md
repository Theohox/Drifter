---
title: Session Digest — Integration Hardening
type: archive
version: "1.0"
status: archived
phase: 3
created: '2026-06-01T16:30:00Z'
updated: '2026-06-01T16:30:00Z'
---

# Session Digest — Integration Hardening (INTEG-001)

## What We Did

Completed Phase 3 Integration Hardening. Turned skeleton integrations into tested, working features.

### 1. Cross-Platform Shell History (`HistoryReader`)

**Problem:** `AgentSelfAuditCheck` and `cmd_audit` only supported bash (`~/.bash_history`). Users on zsh or fish had no audit coverage.

**Solution:** Created `src/drifter/history_reader.py` with a `HistoryReader` class that:
- Auto-detects shell type from `$SHELL` env var or known file paths
- Parses bash (plain text), zsh (with/without timestamps), and fish (YAML-like) formats
- Returns clean command strings for downstream analysis

**Key design decision:** `AgentSelfAuditCheck` remains opt-in (requires explicit `history_path` in config) to respect user privacy. `cmd_audit` (explicit CLI command) uses auto-detection for convenience.

**Tests:** 15 tests covering all 3 shells, auto-detection, max_entries, and edge cases.

### 2. MCP Server Polish

**Problem:** `plugins/mcp-server/server.py` had 0 tests and API mismatches with `ToolInterceptor`.

**Bugs found and fixed:**
- `drifter_classify` called `interceptor.before_shell()` which enforces (raises on block), but classify should return a Classification
- `drifter_enforce` passed `enforce=True` to `before_shell()` — parameter doesn't exist
- `drifter_log` called `interceptor.log_action()` — method doesn't exist; replaced with `SessionLogger.log()`

**Solution:**
- `drifter_classify` now uses `ShellGuard.classify()` directly
- `drifter_enforce` uses `ToolInterceptor.before_shell()` correctly
- `drifter_log` uses `SessionLogger` directly
- Added `ShellGuard` import
- Wrote comprehensive README with install/run instructions

**Tests:** 10 tests covering all 5 MCP tools with valid inputs, blocked commands, approval required, and invalid roots.

### 3. Git Pre-Commit Hook

**Problem:** No way to automatically run `drifter check` before git commits.

**Solution:**
- `drifter install-hook` — writes `.git/hooks/pre-commit` with a robust shell script
- `drifter uninstall-hook` — removes the hook, but only if it was installed by Drifter (safety check)
- Hook tries `drifter`, `python3 -m drifter`, `python -m drifter` in that order
- Hook blocks commit on error-level drift

**Tests:** 6 tests covering install, uninstall, non-git-repo, existing hook, and foreign hook protection.

**Refactoring:** Extracted hook commands to `src/drifter/_hook_commands.py` to keep `cli.py` under its 550-line limit.

## Files Changed

| File | Change |
|------|--------|
| `src/drifter/history_reader.py` | New — cross-platform shell history reader |
| `src/drifter/checks/agent_behavior.py` | Updated — uses `HistoryReader` |
| `src/drifter/cli.py` | Updated — `cmd_audit` uses `HistoryReader`, added `install-hook`/`uninstall-hook` subcommands |
| `src/drifter/_hook_commands.py` | New — extracted hook install/uninstall logic |
| `plugins/mcp-server/server.py` | Fixed — API mismatches, added `ShellGuard` import |
| `plugins/mcp-server/README.md` | Rewrote — proper documentation |
| `tests/test_history_reader.py` | New — 15 tests |
| `tests/test_mcp_server.py` | New — 10 tests |
| `tests/test__hook_commands.py` | New — 6 tests |
| `AGENTS.md` | Updated — mentions `history_reader.py`, new CLI commands |
| `docs/architecture.md` | Updated — added new CLI commands to performance table |
| `docs/project-conductor.md` | Updated — Phase 3 marked complete |
| `drifter-manifest.toml` | Updated — added new files |

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Tests | 159 | 190 (+31) |
| Checks | 34 | 34 |
| Drift Score | 100/100 | 100/100 |

## Decisions

1. **AgentSelfAuditCheck stays opt-in.** Auto-detecting history for a background check felt invasive. Only `cmd_audit` (explicit user action) auto-detects.
2. **MCP tests mock `fastmcp`.** The dependency is optional; tests patch `sys.modules` to avoid requiring installation.
3. **Hook uninstall is defensive.** If a pre-commit hook exists but wasn't installed by Drifter, we refuse to remove it.
4. **Kimi CLI plugin deferred.** It's a stretch goal with lower impact than the three main deliverables.

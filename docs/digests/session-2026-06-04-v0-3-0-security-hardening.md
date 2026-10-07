---
title: Session Digest — v0.3.0 Security Hardening & Anti-Hallucination Stack
type: archive
status: archived
phase: 5
created: '2026-06-04T15:30:00Z'
updated: '2026-10-07T12:00:00Z'
---

# Session Digest — v0.3.0 Security Hardening & Anti-Hallucination Stack (REFACTOR-004)

*Backfilled 2026-10-07 from CHANGELOG `[0.3.0]` and git history (`d09fb71`, `86ad423`, `36244aa`, `63bc571`, `ed91a31`, `d3406ce`). Written after the fact; details reconstructed from commit contents, not memory.*

## What We Did

Completed Phase 5 (Security Hardening) and shipped v0.3.0 on 2026-06-04. Two workstreams landed together: OWASP-review remediation and the anti-hallucination stack.

### 1. Security remediation (OWASP review)

- **Command injection eliminated** — pre-flight step 6 no longer shells out to `grep`; it uses a native Python scan.
- **Session log integrity** — `SessionLogger` entries are HMAC-SHA256 signed with a per-repo secret (`.drifter/.session_secret`, mode 0600; log directory 0700). `SessionLogger.clear()` was removed; `rotate_log()` added as the only sanctioned reset.
- **TOML hardening** — `safe_load_toml()` in `src/drifter/_toml_utils.py`; all check modules migrated to it so corrupt TOML degrades gracefully instead of crashing.
- **Score honesty** — drift score formula capped; health indicator (`clean` / `degraded`) added.
- **GitCommitApprovalCheck strengthened** — scans the last 5 commits for destructive subjects requiring an `[APPROVED BY ...]` marker.
- **AgentSelfAuditCheck timeout** — shell-history reads bounded at 10s.
- **MCP auth** — optional `DRIFTER_MCP_TOKEN` token check on all five MCP tools.
- **CredentialLeakCheck expanded** — credentialed URLs, PEM blocks, AWS keys, high-entropy tokens.
- **Per-check suppression infrastructure** — `ignore_paths` / `ignore_patterns` for every built-in check.

### 2. Anti-hallucination stack

- `src/drifter/manifest_generator.py` — scans the codebase and emits `.drifter/capability-manifest.json`.
- `drifter manifest` and `drifter describe --format json|markdown` CLI commands.
- `GhostReferenceCheck` — detects hallucinated `drifter <command>` and MCP tool references in markdown docs (35th built-in check).
- Self-registering `@mcp_tool` decorator in the MCP server with `get_registered_tools()`.

### 3. Template & lint drift

- Fixed `AGENTS.md` type consistency and command alignment between templates and rendered files (`63bc571`).
- Fixed `ArchitectureDocSyncCheck` multiline regex, Python 3.10 `tomli` fallback, 48 ruff errors, 4 mypy errors (`36244aa`).

## Files Changed

| File | Change |
|------|--------|
| `src/drifter/pre_flight.py` | Native Python keyword scan (no subprocess) |
| `src/drifter/session_logger.py` | HMAC signing, `rotate_log()`, permissions hardening |
| `src/drifter/_toml_utils.py` | New — `safe_load_toml()` |
| `src/drifter/drift_guard.py` | Capped score formula, health indicator |
| `src/drifter/checks/agent_behavior.py` | Last-5-commits approval scan, 10s history timeout |
| `src/drifter/checks/security.py` | Expanded credential patterns |
| `src/drifter/manifest_generator.py` | New — capability manifest generator |
| `src/drifter/checks/ghost_reference.py` | New — GhostReferenceCheck |
| `plugins/mcp-server/server.py` | `@mcp_tool` registry, token auth |
| `src/drifter/cli.py` | `manifest` / `describe` subcommands |

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Tests | 216 | 251 (+35) |
| Checks | 34 | 35 |
| Drift Score | 100/100 | 100/100 |

## Decisions

1. **HMAC over hashing alone** — tamper detection must distinguish forged entries from legitimate ones; a per-repo secret makes cross-repo forgery impractical.
2. **Opt-in MCP auth** — `DRIFTER_MCP_TOKEN` unset means no auth (local-dev default); setting it enforces token checks on every tool call.
3. **Capability manifest is generated, not hand-written** — LLM-facing claims about Drifter's own commands must derive from the code or they become the drift they were meant to prevent.
4. **Memory layer stays deleted** — cross-session persistence happens through digests and the conductor, not a bespoke store.

## Evidence

- Release commit `d3406ce` ("release: v0.3.0 — anti-hallucination stack", 2026-06-04)
- 251 test functions in `tests/` at the release commit (`git grep -h "def test_" d3406ce -- tests | wc -l`)
- CHANGELOG `[0.3.0]` section

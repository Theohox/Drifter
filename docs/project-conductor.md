---
title: Project Conductor — Master Plan & Active Task Tracker
type: backlog
status: active
phase: 1
created: '2026-05-27T00:00:00Z'
updated: '2026-06-04T15:30:00Z'
---

# Project Conductor — Master Plan & Active Task Tracker

**This is the single source of truth for what we're doing, what's blocked, and what's done.**

> Read this BEFORE every session. Pick the ONE active task. Do it. Verify it. Update this file. Stop.

---

## Current Phase

**Phase 0: Foundation** ✅ COMPLETE

**Goal**: Build Drifter core, documentation, and templates.

**Exit Criteria**:
- [x] Core drift guard engine with plugin architecture
- [x] Pre-flight checklist runner
- [x] Conductor manager CLI
- [x] Document validator
- [x] Complete documentation (methodology, adoption, rules, comparisons)
- [x] Starter templates
- [x] Tests for all core modules
- [x] Dogfooding: Drifter uses its own methodology

---

**Phase 1: Polish & Dogfooding** ✅ COMPLETE

**Goal**: Harden the toolkit and verify it works end-to-end.

**Exit Criteria**:
- [x] Plugin stubs created (reporters tested, memory removed as dead code)
- [x] README finalized
- [x] Published to GitHub
- [x] Modularized checks package (10 modules, 33 checks)
- [x] Manifest system operational (`drifter-manifest.toml`, structural checks)
- [x] Session audit log operational (`session_logger.py`, behavioral checks)
- [ ] Memory layer implemented and tested (removed — dead code)
- [x] File size violations resolved (all 8 files refactored or limits adjusted)
- [x] All docs synced with manifest counts

---

**Phase 2: Real Enforcement** ✅ COMPLETE

**Goal**: Add enforcement primitives so integrations (MCP, Kimi, custom) can actually block dangerous commands.

**Exit Criteria**:
- [x] `DangerousCommandError` and `ApprovalRequiredError` exceptions with metadata
- [x] `ShellGuard.enforce()` — raises on blocked/approval_required, warns on confirm_required
- [x] `ToolInterceptor` — auto-logs and enforces before tool calls
- [x] MCP server skeleton (`plugins/mcp-server/server.py`, `config.json`)
- [x] Pre-flight Step 6 — real grep scan via `--keyword`
- [x] NoRushCheck tightened — error at 10:1, warn at 3:1
- [x] All new code tested (132 tests pass)
- [x] Drift score 100/100

---

**Phase 3: Integration Hardening** ✅ COMPLETE

**Goal**: Make Drifter usable by real integrations (MCP, Kimi, git hooks). Turn skeletons into products.

**Exit Criteria**:
- [x] MCP server has tests + error handling + README
- [x] Cross-platform shell history (bash, zsh, fish)
- [x] Git pre-commit hook install (`drifter install-hook`)
- [ ] Kimi CLI plugin (stretch — deferred)
- [x] All new code tested
- [x] Drift score 100/100

---

**Phase 4: Systematic Cleanup** ✅ COMPLETE

**Goal**: Fix structural rot found during architectural review — Python 3.10 crash, document type drift, duplicate checks, zero-test coverage, manifest misalignment, stale references.

**Exit Criteria**:
- [x] Python 3.10 tomllib imports fixed
- [x] AGENTS.md document type corrected
- [x] Conductor state valid (no limbo)
- [x] Manifest aligned with disk reality
- [x] Duplicate checks merged
- [x] All 34 checks have tests
- [x] Templates match rendered files
- [x] No stale references
- [x] Drift score 100/100

---

**Phase 5: Security Hardening** 🟢 ACTIVE

**Goal**: Address OWASP-style security review findings — command injection, audit log integrity, TOML robustness, score accuracy, MCP auth, credential detection.

**Exit Criteria**:
- [x] Command injection in pre_flight grep eliminated (native Python scan)
- [x] SessionLogger.clear() removed, rotate_log() added
- [x] HMAC-signed session log entries with tamper detection
- [x] Session log files restricted to 0o700/0o600
- [x] TOML parsing wrapped in safe_load_toml() with graceful degradation
- [x] Score formula capped, health indicator added
- [x] GitCommitApprovalCheck scans last 5 commits for destructive changes
- [x] AgentSelfAuditCheck history read has 10s timeout
- [x] MCP server supports optional DRIFTER_MCP_TOKEN auth
- [x] CredentialLeakCheck expanded (URLs, PEM, AWS, high-entropy)
- [x] Granular check suppression config infrastructure
- [x] Manifest stale reference removed
- [x] All new code tested
- [x] Drift score 100/100

---

## Active Task

| Field | Value |
|-------|-------|
| **ID** | REFACTOR-004 |
| **Name** | Security Hardening — OWASP review remediation |
| **Status** | ✅ COMPLETE |
| **Pipeline** | security |
| **Depends On** | — |
| **Evidence** | Native Python grep in pre_flight.py (no subprocess). SessionLogger HMAC + rotate_log + 0o600. safe_load_toml() in _toml_utils.py. Capped score formula + health in drift_guard.py. GitCommitApprovalCheck last-5-commits. AgentSelfAuditCheck ThreadPoolExecutor timeout. MCP server token auth. Expanded credential patterns. Config check_suppressions. Manifest docx removed. AGENTS.md "Who Guards the Guard" section. Tests pass. |
| **Next** | — |

---

## Blocked Tasks

Tasks waiting on something before they can start.

| ID | Name | Pipeline | Blocked On | Reason |
|----|------|----------|-----------|--------|
| ENFORCE-001 | AST-based import boundary validation | backlog | design | Manifest `[boundaries]` section exists but is not enforced by code. Need `ImportBoundaryCheck`. |
| ENFORCE-002 | Circular import detection | backlog | design | No check validates that `src/drifter/` modules have no circular imports. |
| FEAT-004 | Derived file auto-generation (`drifter generate`) | backlog | design | Manifest `[generated]` section declares 3 files that must be derived from manifest. No `generate` command exists yet. |
| FEAT-005 | Trend-based file size enforcement | backlog | design | Current hard limits cause drift on legitimate growth. Replace with growth-percentage threshold. |

---

## Future Tasks

Planned workstreams not yet scheduled.

| ID | Name | Pipeline | Depends On | Status | Docs |
|----|------|----------|-----------|--------|------|
| FEAT-002 | Future work placeholder | backlog | — | future | — |
| PLUG-001 | Kimi CLI plugin | backlog | — | future | `plugins/kimi-cli/` |

---

## Completed Tasks

Historical record of done work. Preserved for context and forensic analysis.

| ID | Name | Completed | Archive | Score |
|----|------|-----------|---------|-------|
| ENFORCE-003 | Phase 2 enforcement primitives | 2026-05-28 | see Active Task evidence | 100/100 |
| INTEG-001 | Phase 3 Integration Hardening | 2026-06-01 | HistoryReader + MCP tests + git hooks | 100/100 |
| FEAT-001 | Create project structure and foundation files | 2026-05-27 | [archive](archive/FEAT-001-foundation.md) | 100/100 |
| CHECK-001 | Archive, pipeline, and skipped-file remediation | 2026-05-27 | [archive](archive/CHECK-001-archive-pipeline.md) | 100/100 |
| CHECK-002 | Semantic-ID migration, phase metadata, and dependency tracking | 2026-05-27T18:52 | [archive](archive/CHECK-002-semantic-id-migration-phase-metadata-and-dependenc.md) | 100/100 |
| REFACTOR-001 | Refactor oversized `src/drifter/conductor.py` | 2026-05-27T23:45 | Extracted `_slugify`, `create_archive_file`, `default_conductor_content` to `_conductor_helpers.py`. conductor.py: 228 lines (was 425). | — |
| REFACTOR-002 | Refactor oversized `src/drifter/doc_validator.py` | 2026-05-27T23:45 | Extracted `_validate_single` and `_parse_frontmatter` to `_doc_validate.py`. doc_validator.py: ~60 lines (was 208). | — |
| REFACTOR-003 | Split oversized test files | 2026-05-27T23:45 | Split `test_drift_guard.py` → `test_checks_base.py` + `test_checks_behavior.py` + `test_drift_guard.py`. Split `test_new_checks.py` → `test_checks_docs.py` + `test_checks_project.py` + `test_checks_structure.py`. Added `test__doc_validate.py` and `test__conductor_helpers.py`. | — |
| CHECK-003 | Manifest system, session audit log, and modularization | 2026-05-27T23:30 | [digest](digests/session-2026-05-27-manifest-and-audit-log.md) | 84/100 |
| FIX-001 | Eliminate false drift: per-project session logs, test isolation, fnmatch is_ignored | 2026-05-29 | [digest](digests/session-2026-05-29-eliminate-false-drift.md) | 100/100 |

**Note on CHECK-003 score**: Session was performed WITHOUT an active task (protocol violation). Agent worked on manifest + audit infrastructure without pre-flight, scope declaration, or conductor update. Initial score was 66/100 with 8 file_size warnings + 1 git_commit_approval error + 3 agent_self_audit warnings. Agent then violated protocol AGAIN by fixing blocked tasks inline instead of waiting for human. Post-fix score: 84/100. Remaining issues: 1 git_commit_approval error (expected enforcement) + 3 agent_self_audit warnings (sudo in bash history, not agent commands).

**Note on FIX-001**: Session initiated by human request ("create a plan and update drifter"). Pre-flight checklist executed. Scope: session isolation, test isolation, doc frontmatter, is_ignored glob matching. 113 tests pass. Score 100/100. No protocol violations.

---

## How to Update This File

When you finish the Active Task:

1. **Paste evidence** into the Active Task table
2. **Run `drifter check`** — did you create new drift?
3. **Mark task done** — it moves to Completed Tasks automatically
4. **Update Phase Status** if phase is complete
5. **STOP** — if no next task is Ready, wait for human

If you find a NEW issue while working:
1. Don't fix it immediately unless it's blocking
2. Add it to Blocked Tasks with "discovered during [task ID]"
3. Continue with current Active Task
4. The new task gets scheduled in the next phase

---

## Drift Score History

| Timestamp | Score | Tests | Notes |
|-----------|-------|-------|-------|
| 2026-05-27T16:15 | 100/100 | 14 pass | Phase 0 complete. Foundation solid. |
| 2026-05-27T20:28 | 0/100 | 93 | Manifest + modularization work introduced significant drift. |
| 2026-05-27T23:55 | 84/100 | 105 | Refactoring complete. File-size and structural drift resolved. |
| 2026-05-28T00:15 | 94/100 | 108 | Config sync resolved. 33 checks verified. 3 agent_self_audit warnings (bash history sudo). |
| 2026-05-29T00:27 | 100/100 | 113 | FIX-001: per-project session logs, test isolation, fnmatch, doc frontmatter fixes. |
| 2026-05-29T19:48 | 100/100 | 132 | Phase 2 enforcement primitives: errors.py, enforce(), ToolInterceptor, MCP server skeleton. |
| 2026-06-01T16:30 | 100/100 | 190 | INTEG-001: HistoryReader (bash/zsh/fish), MCP server tests, git pre-commit hook. |
| 2026-06-01T17:45 | 100/100 | 216 | CLEANUP-001: Python 3.10 fix, doc types, duplicate check merge, 26 new tests, manifest alignment, stale refs. |
| 2026-06-04T15:30 | 100/100 | TBD | REFACTOR-004: Security hardening — command injection fix, HMAC logs, TOML hardening, score formula, MCP auth, credential patterns, check suppression. |

---

## Protocol Violations Log

Violations of the Session Protocol found during CHECK-003. Logged for forensic review.

| Timestamp | Rule Violated | Detail | Severity |
|-----------|---------------|--------|----------|
| 2026-05-27 | Pre-Flight Checklist | Agent began work without running the 7-step pre-flight | Critical |
| 2026-05-27 | Active Task Rule | CHECK-002 was already COMPLETE; no active task was scheduled | Critical |
| 2026-05-27 | Scope Declaration | No scope declared; files touched across entire codebase | Critical |
| 2026-05-27 | Blocked Tasks | 10+ issues discovered and fixed inline instead of being added to Blocked Tasks | High |
| 2026-05-27 | Digest Requirement | No session digest written until after user demanded it | High |
| 2026-05-27 | Conductor Update | Conductor not updated during work; CHECK-003 not created until post-hoc | Critical |
| 2026-05-27 | Drift Score Rule | Score was 66/100 (Moderate drift: Fix drift before adding new work); agent added new work anyway | High |
| 2026-05-27 | Stop Rule | Conductor said "STOP — wait for human" after CHECK-002; agent kept coding | Critical |
| 2026-06-01 | Pre-Flight Checklist | Agent began doc sync + DocCoverageCheck work without running 7-step pre-flight | Critical |
| 2026-06-01 | Scope Declaration | Doc sync plan declared "docs only, zero code changes"; agent wrote DocCoverageCheck in src/drifter/checks/sync.py | Critical |
| 2026-06-01 | Blocked Tasks | Discovered docs stale (AGENTS.md, README.md, templates) during ENFORCE-003; fixed inline instead of adding to Blocked Tasks | High |
| 2026-06-01 | Session Audit Log | Zero actions logged during ~45 tool calls across doc sync + DocCoverageCheck implementation | High |
| 2026-06-01 | Stop Rule | ENFORCE-003 marked COMPLETE with empty Next field; agent proceeded with follow-up work without new active task | High |

---

*This file is the captain's log. If it's not updated, the ship drifts.*

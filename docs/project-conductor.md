---
title: Project Conductor — Master Plan & Active Task Tracker
type: backlog
status: active
phase: 1
created: '2026-05-27T00:00:00Z'
updated: '2026-05-27T19:17:12Z'
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

**Phase 1: Polish & Dogfooding** 🟢 ACTIVE

**Goal**: Harden the toolkit and verify it works end-to-end.

**Exit Criteria**:
- [x] Plugin stubs created (reporters tested, memory removed as dead code)
- [x] README finalized
- [x] Published to GitHub
- [ ] Memory layer implemented and tested (removed — dead code)

---

## Active Task

| Field | Value |
|-------|-------|
| **ID** | CHECK-002 |
| **Name** | Semantic ID migration, phase metadata, and dependency tracking |
| **Status** | ✅ COMPLETE
| **Pipeline** | active |
| **Depends On** | CHECK-001 |
| **Evidence** | MIGRATE: Task IDs D.1→FEAT-001, D.2→CHECK-001, D.3→FEAT-002, M.1→FEAT-003, P.1→PLUG-001, P.2→PLUG-002. NET NEW: phase: metadata on all 9 docs, docs/phase-index.md. UPDATE: conductor Depends On column, PipelineIntegrityCheck validates deps + cycles, doc_validator validates phase:. Archive folder built: docs/archive/ with auto-archive in mark_done(), ArchiveIntegrityCheck (19th check).
| **Next** | FEAT-002 |

---

## Blocked Tasks

Tasks waiting on something before they can start.

| ID | Name | Pipeline | Depends On | Blocked On | ETA |
|----|------|----------|-----------|-----------|-----|
| — | — | — | — | — | — |

---

## Future Tasks

Planned workstreams not yet scheduled.

| ID | Name | Pipeline | Depends On | Status | Docs |
|----|------|----------|-----------|--------|------|
| FEAT-002 | Future work placeholder | backlog | — | future | — |
| FEAT-003 | Memory layer (claude-mem inspired) | backlog | — | future | `src/memory/` |
| PLUG-001 | Kimi CLI plugin | backlog | — | future | `plugins/kimi-cli/` |
| PLUG-002 | MCP server plugin | backlog | — | future | `plugins/mcp-server/` |

---

## Completed Tasks

Historical record of done work. Preserved for context and forensic analysis.

| ID | Name | Completed | Archive | Score |
|----|------|-----------|---------|-------|
| FEAT-001 | Create project structure and foundation files | 2026-05-27 | [archive](archive/FEAT-001-foundation.md) | 100/100 |
| CHECK-001 | Archive, pipeline, and skipped-file remediation | 2026-05-27 | [archive](archive/CHECK-001-archive-pipeline.md) | 100/100 |
| CHECK-002 | Semantic ID migration, phase metadata, and dependency tracking | | 2026-05-27T18:52 | [archive](archive/CHECK-002-semantic-id-migration-phase-metadata-and-dependenc.md) | — |

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
| 2026-05-27T17:24 | 100/100 | 0 | Auto-updated by drifter check |
| 2026-05-27T17:25 | 100/100 | 0 | Auto-updated by drifter check |
| 2026-05-27T17:26 | 56/100 | 0 | Auto-updated by drifter check |
| 2026-05-27T17:30 | 62/100 | 0 | Score-only run |
| 2026-05-27T17:30 | 78/100 | 0 | Auto-updated by drifter check |
| 2026-05-27T17:33 | 98/100 | 0 | Auto-updated by drifter check |
| 2026-05-27T17:33 | 100/100 | 0 | Auto-updated by drifter check |
| 2026-05-27T17:34 | 100/100 | 0 | Score-only run |
| 2026-05-27T17:34 | 100/100 | 0 | Score-only run |
| 2026-05-27T17:35 | 100/100 | 0 | Score-only run |
| 2026-05-27T17:35 | 100/100 | 0 | Auto-updated by drifter check |
| 2026-05-27T17:35 | 100/100 | 62 | Auto-updated by drifter check |
| 2026-05-27T17:36 | 100/100 | 62 | Auto-updated by drifter check |
| 2026-05-27T17:45 | 100/100 | 62 | Score-only run |
| 2026-05-27T18:09 | 94/100 | 66 | Auto-updated by drifter check |
| 2026-05-27T18:10 | 98/100 | 66 | Auto-updated by drifter check |
| 2026-05-27T18:10 | 100/100 | 66 | Auto-updated by drifter check |
| 2026-05-27T18:35 | 100/100 | 66 | Auto-updated by drifter check |
| 2026-05-27T18:41 | 96/100 | 72 | Score-only run |
| 2026-05-27T18:41 | 98/100 | 72 | Auto-updated by drifter check |
| 2026-05-27T18:42 | 100/100 | 72 | Score-only run |
| 2026-05-27T18:42 | 100/100 | 72 | Auto-updated by drifter check |
| 2026-05-27T18:55 | 100/100 | 72 | Auto-updated by drifter check |
| 2026-05-27T18:57 | 100/100 | 84 | Auto-updated by drifter check |
| 2026-05-27T18:57 | 100/100 | 84 | Auto-updated by drifter check |
| 2026-05-27T18:58 | 92/100 | 84 | Auto-updated by drifter check |
| 2026-05-27T18:59 | 100/100 | 84 | Auto-updated by drifter check |
| 2026-05-27T18:59 | 98/100 | 84 | Auto-updated by drifter check |
| 2026-05-27T18:59 | 100/100 | 84 | Auto-updated by drifter check |
| 2026-05-27T19:03 | 100/100 | 84 | Auto-updated by drifter check |
| 2026-05-27T19:03 | 100/100 | 84 | Auto-updated by drifter check |
| 2026-05-27T19:16 | 98/100 | 84 | Auto-updated by drifter check |
| 2026-05-27T19:17 | 100/100 | 84 | Auto-updated by drifter check |

---

*This file is the captain's log. If it's not updated, the ship drifts.*

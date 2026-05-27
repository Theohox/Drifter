---
title: Project Conductor — Master Plan & Active Task Tracker
type: backlog
status: active
created: '2026-05-27T00:00:00Z'
updated: '2026-05-27T00:00:00Z'
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
- [ ] Memory layer implemented and tested
- [ ] Plugin stubs created
- [ ] README finalized
- [ ] Published to GitHub

---

## Active Task

| Field | Value |
|-------|-------|
| **ID** | D.1 |
| **Name** | Create project structure and foundation files |
| **Status** | ✅ COMPLETE |
| **Evidence** | `drifter check` score: 100/100. All tests pass (14/14). |
| **Next** | D.2: Dogfooding and polish |

---

## Blocked Tasks

Tasks waiting on something before they can start.

| ID | Name | Blocked On | ETA |
|----|------|-----------|-----|
| — | — | — | — |

---

## Future Tasks

Planned workstreams not yet scheduled.

| ID | Name | Status | Docs |
|----|------|--------|------|
| M.1 | Memory layer (claude-mem inspired) | future | `src/memory/` |
| P.1 | Kimi CLI plugin | future | `plugins/kimi-cli/` |
| P.2 | MCP server plugin | future | `plugins/mcp-server/` |

---

## How to Update This File

When you finish the Active Task:

1. **Paste evidence** into the Active Task table (test output, command output, file diff)
2. **Update Phase Status** if phase is complete
3. **Run Drift Guard** — did you create new drift?
4. **STOP** — if no next task is Ready, wait for human

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

---

*This file is the captain's log. If it's not updated, the ship drifts.*

---
title: Drifter Comparisons
type: reference
status: active
created: '2026-05-27T00:00:00Z'
updated: '2026-05-27T00:00:00Z'
---

# Drifter Comparisons

How Drifter compares to other approaches for controlling AI agents.

---

## Drifter vs `.cursorrules`

[Cursor](https://cursor.sh) uses `.cursorrules` files to provide context to its AI agent. This is the most common alternative to Drifter.

| Aspect | `.cursorrules` | Drifter |
|--------|---------------|---------|
| **Form** | Single file, static prompt | Multi-file system: contract, rules, conductor, drift guard |
| **Enforcement** | None — the AI may ignore it | `drifter preflight` gates coding; `drifter check` catches drift |
| **Persistence** | Per-session prompt injection | Persistent project state via conductor and digests |
| **Scope control** | None | Scope boundary rule + conductor active task |
| **Evidence** | None | Evidence rule requires proof before "done" |
| **Drift detection** | None | Automated stale reference and hardcoded path detection |
| **Document types** | None | Document type system prevents doc-code divergence |

**Verdict:** `.cursorrules` is a prompt. Drifter is a system. Use `.cursorrules` for stylistic preferences (naming conventions, formatting). Use Drifter for structural discipline (don't recreate, stay in scope, prove it works).

**Can they coexist?** Yes. Put stylistic rules in `.cursorrules`. Put structural rules in Drifter. Drifter's `AGENTS.md` can reference `.cursorrules` for style, and `.cursorrules` can reference Drifter for process.

---

## Drifter vs Claude-Mem

[Claude-Mem](https://github.com/thedotmack/claude-mem) is a persistent memory system for Claude Code. It captures session observations, compresses them, and injects relevant context into future sessions.

| Aspect | Claude-Mem | Drifter |
|--------|-----------|---------|
| **Problem solved** | Memory (cross-session context) | Discipline (enforced protocols) |
| **Mechanism** | SQLite + Chroma vector DB + lifecycle hooks | Pre-flight gates + drift guard + document types |
| **Agent awareness** | Transparent to agent (injected automatically) | Explicit (agent must read conductor, run checks) |
| **Scope control** | None | Conductor tracks one active task |
| **Drift detection** | None | Core feature |
| **Document types** | None | Core feature |

**Verdict:** They solve different problems. Claude-Mem remembers what happened. Drifter prevents mistakes from happening.

**Can they coexist?** Yes, and they should. Use Claude-Mem for cross-session memory ("remember that we tried X and it failed"). Use Drifter for session-level discipline ("don't start coding until you've read the conductor"). Drifter's digest system produces the observations that Claude-Mem would capture.

---

## Drifter vs AI Coding Agents' Built-In Planning

Modern AI coding agents (Claude Code, GitHub Copilot Workspace, etc.) have built-in planning capabilities. They can create task lists, reason about dependencies, and execute multi-step plans.

| Aspect | Built-In Planning | Drifter |
|--------|------------------|---------|
| **Plan ownership** | Agent-generated, ephemeral | Human-defined, persistent |
| **Plan location** | In-session context | `docs/project-conductor.md` (versioned) |
| **Plan enforcement** | Agent may deviate | Conductor authority rule: agent must follow |
| **Cross-session** | Lost when session ends | Persistent across all sessions |
| **Verification** | Agent self-reports | Evidence rule + drift guard |
| **Scope control** | Agent decides scope | Human defines scope via conductor |

**Verdict:** Built-in planning is useful for tactical execution within a task. Drifter is necessary for strategic control of what tasks exist and which one is active.

**Can they coexist?** Yes. Use the agent's built-in planning to break down the active task from the conductor. The conductor says "implement user auth"; the agent plans the steps. The conductor prevents the agent from switching to "refactor the database" mid-session.

---

## Drifter vs Traditional Linting/Static Analysis

Tools like ESLint, Pylint, MyPy, and Rust's Clippy catch code-level issues. Drifter catches documentation-level and process-level issues.

| Aspect | Traditional Linting | Drifter |
|--------|-------------------|---------|
| **Target** | Code correctness | Documentation correctness + process discipline |
| **Rules** | Language-specific | Language-agnostic |
| **Drift detection** | None (catches style/bugs, not doc-code divergence) | Core feature |
| **Process enforcement** | None | Pre-flight protocol |
| **Scope control** | None | Conductor |

**Verdict:** They are complementary. Run traditional linters in CI. Run Drifter in CI too. They catch different classes of problems.

---

## Drifter vs Code Review

Human code review catches many of the same problems Drifter catches: recreation, scope creep, missing tests. But code review happens *after* the code is written.

| Aspect | Code Review | Drifter |
|--------|------------|---------|
| **Timing** | After code is written | Before and during coding |
| **Cost** | Human time (expensive) | Automated (cheap) |
| **Consistency** | Varies by reviewer | Deterministic |
| **Scale** | Doesn't scale with agent velocity | Scales automatically |
| **Process** | None | Enforced pre-flight and stop rules |

**Verdict:** Code review is still valuable for architectural judgment and edge cases. Drifter catches the 80% of routine mistakes that don't need human attention.

---

## Summary Matrix

| Approach | Memory | Discipline | Drift Detection | Scope Control | Cross-Session |
|----------|--------|-----------|-----------------|---------------|---------------|
| `.cursorrules` | ❌ | ❌ | ❌ | ❌ | ❌ |
| Claude-Mem | ✅ | ❌ | ❌ | ❌ | ✅ |
| Built-in Planning | ❌ | ⚠️ Weak | ❌ | ❌ | ❌ |
| Traditional Linting | ❌ | ❌ | ❌ | ❌ | ❌ |
| Code Review | ❌ | ⚠️ Reactive | ⚠️ Manual | ⚠️ Manual | ❌ |
| **Drifter** | ❌* | ✅ | ✅ | ✅ | ✅** |

\* Drifter does not provide memory. Pair with Claude-Mem or digests for memory.  
\** Drifter provides cross-session persistence via conductor and digests, but not automatic context injection.

---

*This document is a reference. Update it when new tools emerge.*

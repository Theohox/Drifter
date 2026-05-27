# Drifter — Universal AI Agent Drift Guard

> **Before you write a single line of code, know what already exists.**

Drifter is a methodology and toolkit that forces AI agents to follow standard rules before touching code. It prevents the four failure modes of agentic coding:

1. **Hallucination** — inventing files, APIs, or patterns that don't exist
2. **Bloat** — adding unnecessary code, dependencies, or complexity
3. **Context blindness** — editing without reading the whole codebase
4. **Drift** — docs, code, and reality diverging over time

Drifter is not a prompt. It is a **system of enforced protocols** — pre-flight checklists, 23 automated drift checks, document type constraints, and a project conductor that keeps agents focused on one thing at a time.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/Theohox/Drifter.git
cd Drifter

# Run the drift guard on itself
PYTHONPATH=src python3 -m drifter.cli check

# Initialize in any project
cd your-project
PYTHONPATH=../Drifter/src python3 -m drifter.cli init

# Run pre-flight before a coding session
PYTHONPATH=../Drifter/src python3 -m drifter.cli preflight --task "fix login bug"
```

## What You Get

| Artifact | Purpose |
|----------|---------|
| `AGENTS.md` (repo root) | Canonical agent contract. Read first, every session. |
| `dangerous_patterns.toml` | Command boundaries. Agents read this before running shell. |
| `docs/session-protocol.md` | Hard rules: scope, evidence, no-recreation, stop rule. |
| `docs/project-conductor.md` | Single source of truth: what's active, blocked, done. |
| `docs/archive/README.md` | Completed task records. One file per finished task. |
| `drifter check` | 23 automated checks: stale refs, hardcoded paths, doc drift, credential leaks, dead code, and more. |
| `drifter preflight` | Enforced 7-step pre-flight before any code change. |
| `drifter conductor` | CLI for managing active tasks and phase state. |
| `drifter validate` | Validate document types and frontmatter. |
| `drifter audit` | Audit session history for dangerous command violations. |
| `drifter init` | Initialize Drifter in a new project. |

## The 7-Step Pre-Flight

Every session starts with this exact sequence:

1. **READ** `AGENTS.md` — the agent contract
2. **READ** `docs/session-protocol.md` — hard rules
3. **READ** `docs/project-conductor.md` — what's active?
4. **RUN** `drifter check` — what's the current drift?
5. **PICK** one active task from the conductor
6. **GREP** for existing code before writing new code
7. **READ** `dangerous_patterns.toml` — command boundaries before running shell

No exceptions. No "I'll just quickly fix this one thing."

## Philosophy

Reactive prompting fails because agents ignore long prompts under pressure. Proactive enforcement works because **scripts + structure > words**.

Drifter treats documentation as a correctness layer, not an afterthought. Every document has a **type** with mutation rules:

| Type | Example | Rule |
|------|---------|------|
| **Constitution** | `AGENTS.md` | Stable principles. Rarely changes. |
| **Snapshot** | `docs/digests/index.md` | Current truth only. Rewrite, don't append. |
| **Backlog** | `docs/project-conductor.md` | Open work only. Remove items when done. |
| **Archive** | `docs/archive/` | One file per completed task. Auto-generated on `mark_done()`. |
| **Playbook** | `docs/session-protocol.md` | Operational procedures. Update when process changes. |
| **Index** | `docs/phase-index.md` | Maps all docs to their phase without moving files. |

When every doc knows its type, docs don't become lies.

## How Drifter Compares

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

**Verdicts:**
- **vs `.cursorrules`** — `.cursorrules` is a prompt. Drifter is a system. Use both: style in `.cursorrules`, structure in Drifter.
- **vs Claude-Mem** — Claude-Mem remembers what happened. Drifter prevents mistakes from happening. Use both.
- **vs Built-in Planning** — Agent planning is tactical execution. The conductor is strategic control of what tasks exist.
- **vs Linting** — Linters catch code issues. Drifter catches documentation and process drift. Complementary.
- **vs Code Review** — Review catches the 20% that needs human judgment. Drifter catches the 80% of routine mistakes automatically.

## Documentation

- [`docs/methodology.md`](docs/methodology.md) — The "why" in detail
- [`docs/adoption-guide.md`](docs/adoption-guide.md) — Step-by-step for any project
- [`docs/rules-reference.md`](docs/rules-reference.md) — Complete rule catalog

## License

MIT

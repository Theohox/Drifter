# Drifter Agent Contract

*Read this FIRST before touching any code. Every. Single. Time.*

## 0. The Golden Rule

> **Before you write a single line of code, grep the codebase for what already exists.**

Drifter is a young project with a clear architecture. If you think "I should build X", first check if X already exists.

## 1. Pre-Flight Checklist (Do This First)

Before any coding session:

- [ ] **Read this prompt** (you are here)
- [ ] **Read the Session Protocol**: `docs/session-protocol.md`
- [ ] **Read the Conductor**: `docs/project-conductor.md`
- [ ] **Run Drift Guard**: `python -m drifter check`
- [ ] **Check the digest index**: `docs/digests/index.md`
- [ ] **Grep for existing functionality**: `grep -r "your_idea" src/ tests/`
- [ ] **Run tests**: `python -m pytest tests/ -q`

**If you skip this checklist, you will recreate existing code.**

## 2. Architecture Boundaries

| Component | Location | Don't Do |
|-----------|----------|----------|
| Core drift detection | `src/drifter/drift_guard.py` | Keep it plugin-based. Don't hardcode project-specific checks. |
| Pre-flight runner | `src/drifter/pre_flight.py` | Don't add agent-specific logic. Universal rules only. |
| Conductor manager | `src/drifter/conductor.py` | Don't auto-pick tasks. Humans/agents must explicitly choose. |
| Document validator | `src/drifter/doc_validator.py` | Don't validate content, only structure and type rules. |
| Memory layer | `src/memory/` | Optional dependency. Core must work without it. |
| Reporters | `src/reporters/` | Each reporter is independent. Don't couple output formats. |
| Templates | `templates/` | Annotated templates, not generated content. |
| Plugins | `plugins/` | Agent-specific integrations. Core must not depend on plugins. |

## 3. What Already Exists (Don't Recreate)

| What You Need | Where It Already Exists |
|---------------|------------------------|
| Run drift guard | `python -m drifter check` or `src/drifter/drift_guard.py` |
| Run pre-flight | `python -m drifter preflight` or `src/drifter/pre_flight.py` |
| Manage conductor | `python -m drifter conductor` or `src/drifter/conductor.py` |
| Validate docs | `python -m drifter validate` or `src/drifter/doc_validator.py` |
| Add a new check | `src/drifter/drift_guard.py` — implement `Check` protocol |
| Add a reporter | `src/drifter/reporters/` — implement `Reporter` protocol |
| Project config | `pyproject.toml [tool.drifter]` or `drifter.toml` |

## 4. Critical Rules

### The Scope Boundary Rule
Before touching any file, declare:

> "I will only touch **[file]** for **[reason]**. I will not touch [related files]."

If you discover a related issue while working:
- Add it to Blocked Tasks in the Conductor
- Do NOT fix it immediately
- Finish your scoped task first

### The Evidence Rule
Every "done" task must have evidence:

| Task Type | Required Evidence |
|---|---|
| Code change | Test output showing pass |
| Doc update | `grep` showing no stale refs |
| New check | Test in `tests/` proving it detects the drift class |
| Template change | Rendered output showing correct structure |

No evidence = not done.

### The Stop Rule
When you finish the Active Task:

```
1. RUN tests (pytest)
2. RUN drift guard again — did you create new drift?
3. UPDATE Conductor — mark done, paste evidence
4. STOP — if no next task is Ready, wait for hox
```

### The No-Recreation Rule
If you think "I should build X":

1. Grep for X in the codebase
2. Check `docs/digests/index.md` for existing digests
3. Check `src/` — does it already exist under a different name?

**If X exists in any form, use it. Do not recreate.**

### The Test Rule
Every new check, reporter, or core function gets a test. Drifter is a correctness tool. It must be correct.

```bash
python -m pytest tests/ -q
```

**If tests fail, fix before declaring done.**

## 5. Document Types

Every markdown file in `docs/` MUST have a `type:` in its frontmatter:

- `constitution` — stable principles (`docs/methodology.md`)
- `snapshot` — current truth, rewrite don't append (`docs/architecture.md`)
- `backlog` — open work only (`docs/project-conductor.md`)
- `archive` — completed work with context
- `playbook` — operational procedures (this file)
- `guide` — how-to documentation (`docs/adoption-guide.md`)
- `reference` — lookup docs (`docs/rules-reference.md`)

**Wrong type = drift.** Fix it.

## 6. Communication Protocol

**When reporting to hox:**

1. **Lead with the answer, not the process.**
2. **If you don't know, say so.** Never hallucinate file contents.
3. **If you recreated something, admit it.**
4. **Update digests.** Every session produces a digest.

## 7. Quick Reference

```bash
python -m drifter check              # Run drift guard
python -m drifter preflight          # Run pre-flight checklist
python -m drifter conductor show     # Show active task
python -m drifter validate           # Validate document types
python -m pytest tests/ -q           # Run tests
ruff check src/ tests/               # Lint
mypy src/                            # Type check
```

## 8. If You're Stuck

**Before asking hox:**

1. Read this prompt again.
2. Check `docs/digests/index.md`
3. Grep the codebase.
4. Read the README.

**If you still need help:** Say exactly what you checked and found.

---

*This is a living document. Canonical location: repo root (`AGENTS.md`).*
*Created: 2026-05-27 | Purpose: Prevent agents from reinventing the drift guard.*

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
- [ ] **Read dangerous_patterns.toml**: command boundaries before running shell

**If you skip this checklist, you will recreate existing code.**

## 2. Architecture Boundaries

| Component | Location | Don't Do |
|-----------|----------|----------|
| Core drift detection | `src/drifter/drift_guard.py` | Keep it plugin-based. Don't hardcode project-specific checks. |
| Pre-flight runner | `src/drifter/pre_flight.py` | Don't add agent-specific logic. Universal rules only. |
| Conductor manager | `src/drifter/conductor.py` | Don't auto-pick tasks. Humans/agents must explicitly choose. |
| Document validator | `src/drifter/doc_validator.py` | Don't validate content, only structure and type rules. |
| Reporters | `src/drifter/reporters/` | Each reporter is independent. Don't couple output formats. |
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
| Audit session | `drifter audit` or `src/drifter/shell_guard.py` |
| Add a new check | `src/drifter/drift_guard.py` — implement `Check` protocol |
| Add a reporter | `src/drifter/reporters/` — implement `Reporter` protocol |
| Project config | `drifter.toml` (`[drifter]` section) or `pyproject.toml [tool.drifter]` |

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

### The Dangerous Patterns Rule
**Before running ANY shell command, read `dangerous_patterns.toml` at repo root.**

This file is the canonical enforcement spec. It is not a suggestion. It is the single source of truth for what commands are forbidden.

| Classification | Action | Example |
|----------------|--------|---------|
| `always_block` | ❌ NEVER run | `git commit`, `git push`, `rm -rf /` |
| `blocked` | ❌ NEVER run | `dd if=`, `curl | sh` |
| `approval_required` | ⚠️ Ask human first | `git add` |
| `confirm_required` | ⚠️ Confirm with human | `sudo`, `rm -rf` |
| `allowed` | ✅ Proceed | `git status`, `git diff` |

**How to check:**
```python
from drifter.shell_guard import ShellGuard
guard = ShellGuard()
print(guard.check("git commit -m x"))  # BLOCKED
print(guard.check("git status"))       # ALLOWED
```

**If dangerous_patterns.toml does not exist, STOP and create it.** This file is as critical as AGENTS.md.

### The Git Boundary Rule — ABSOLUTE

**Agents do not commit. Agents do not push. EVER.**

| Command | Allowed? | Condition |
|---------|----------|-----------|
| `git status`, `git diff`, `git log` | ✅ Yes | Informational only |
| `git add` | ⚠️ Only if explicitly asked | Never assume |
| `git commit`, `git push` | ❌ NEVER | Human's job |
| `git reset`, `git rebase`, `git merge` | ❌ NEVER | History-mutating |
| `git checkout -b`, `git tag`, `git cherry-pick` | ❌ NEVER | History-mutating |

**ABSOLUTE RULES:**
1. **Each commit requires FRESH explicit approval.** Prior approval never rolls forward. "Commit that yesterday" = expired. Ask again today.
2. **Approval must be verbatim.** The human must say something like "commit and push" or "you may commit." IMPLIED approval ("ok", "proceed", "looks good", "C") is NOT sufficient.
3. **If you committed without approval, STOP.** Do not commit again. Report the violation immediately. The human decides whether to revert.
4. **If `drifter check` fails because of AgentSelfAuditCheck or GitCommitApprovalCheck, you violated the rule.** Stop working. Report it. Ask for instructions.

**NO EXCUSES:**
- "It was small" — NOT AN EXCUSE.
- "The user would want it" — NOT AN EXCUSE. You cannot read minds.
- "I forgot" — NOT AN EXCUSE. The check exists so you don't forget.
- "It was an emergency" — NOT AN EXCUSE. There is no git emergency that requires bypassing the human.

The human reviews changes in the Git Panel and decides when to commit/push. The agent writes code; the human owns the timeline.

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

## 6. Canonical Documents

Every document in `docs/` is canonical. Read the right one at the right time:

| Document | Read when... | Type |
|----------|-------------|------|
| `docs/methodology.md` | You need to understand WHY a rule exists | constitution |
| `docs/session-protocol.md` | Before every coding session | playbook |
| `docs/project-conductor.md` | Before every coding session | backlog |
| `docs/rules-reference.md` | You need the complete rule catalog | reference |
| `docs/architecture.md` | You're changing Drifter internals | snapshot |
| `docs/adoption-guide.md` | You're adopting Drifter in a new project | guide |
| `docs/document-types.md` | You're unsure what type a doc should be | reference |
| `docs/phase-index.md` | You want to know what was built in each phase | index |
| `docs/digests/index.md` | You want to see past session records | snapshot |

---

## 7. Communication Protocol

**When reporting to hox:**

1. **Lead with the answer, not the process.**
2. **If you don't know, say so.** Never hallucinate file contents.
3. **If you recreated something, admit it.**
4. **Update digests.** Every session produces a digest.

## 8. Session Audit Log — NON-NEGOTIABLE

Every tool call you make is recorded in an append-only log. Checks verify behavioral patterns from this log. **If the log shows you rushed, appended without reading, or skipped tests, you cannot declare the task done.**

### How to Log

After every significant action, log it:

```bash
# After ReadFile
drifter log READ /path/to/file

# After WriteFile or StrReplaceFile
drifter log WRITE /path/to/file

# After Shell
drifter log SHELL "command you ran"

# After drifter check
drifter log CHECK "drifter check passed 84/100"
```

**If you forget to log, the session report will fail. The log is your proof of diligence.**

### Before Declaring "Done"

Run the session report:

```bash
drifter session-report
```

It produces a report card. If it fails, you are not done. Fix the violations.

### What the Report Card Checks

| Check | What It Verifies | Severity |
|-------|-----------------|----------|
| **ReadBeforeWrite** | Every WRITE had a preceding READ | error |
| **TestAfterWrite** | Last WRITE was followed by a test run | error |
| **DriftCheckAfterWrite** | Last WRITE was followed by `drifter check` | error |
| **NoRush** | At least one drift check per 3 WRITEs | warn |

**Why this exists**: The #1 failure mode of AI agents is append-only coding without reading existing code. This log forces you to prove you read before you wrote.

## 9. Quick Reference

```bash
python -m drifter check              # Run drift guard
python -m drifter preflight          # Run pre-flight checklist
python -m drifter conductor show     # Show active task
python -m drifter validate           # Validate document types
python -m drifter audit              # Audit session for dangerous commands
python -m drifter init               # Initialize Drifter in a new project
python -m pytest tests/ -q           # Run tests
ruff check src/ tests/               # Lint
mypy src/                            # Type check
```

## 10. If You're Stuck

**Before asking hox:**

1. Read this prompt again.
2. Check `docs/digests/index.md`
3. Check `docs/rules-reference.md` for the complete rule catalog.
4. Grep the codebase.
5. Read the README.

**If you still need help:** Say exactly what you checked and found.

---

*This is a living document. Canonical location: repo root (`AGENTS.md`).*
*Created: 2026-05-27 | Purpose: Prevent agents from reinventing the drift guard.*

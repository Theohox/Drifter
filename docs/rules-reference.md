---
title: Drifter Rules Reference
type: reference
status: active
phase: 0
created: '2026-05-27T00:00:00Z'
updated: '2026-05-27T22:47:28Z'
---

# Drifter Rules Reference

Complete catalog of all rules in the Drifter methodology.

---

## The Golden Rule

> **Before you write a single line of code, grep the codebase for what already exists.**

**Why:** Recreation is the root cause of bloat. Agents that search first write less code.

**How:**
```bash
grep -r "your_idea" src/ tests/
find . -name "*similar*" -type f
```

**Enforcement:** Pre-flight protocol step 6. Drift guard can be extended with project-specific checks.

---

## The 7-Step Pre-Flight

Every session must follow this exact sequence:

1. **READ** `AGENTS.md` — the agent contract
2. **READ** `docs/session-protocol.md` — hard rules
3. **READ** `docs/project-conductor.md` — what's active?
4. **RUN** `drifter check` — what's the current drift?
5. **PICK** one active task from the conductor
6. **GREP** for existing code before writing new code
7. **READ** `dangerous_patterns.toml` — command boundaries before running shell

**Why:** Forces context loading before code generation. Prevents agents from starting with a blank slate.

**Enforcement:** `drifter preflight` command. Non-zero exit code if any step fails.

---

## The Scope Boundary Rule

Before touching any file, declare:

> "I will only touch **[file]** for **[reason]**. I will not touch [related files]."

If you discover a related issue while working:
- Add it to Blocked Tasks in the Conductor
- Do NOT fix it immediately
- Finish your scoped task first

**Why:** Prevents rabbit holes. Agents that fix everything they see never finish anything.

**Enforcement:** Session protocol. Agent must declare scope before editing.

---

## The Evidence Rule

Every "done" task must have evidence:

| Task Type | Required Evidence |
|---|---|
| Code change | Test output showing pass |
| Bug fix | Before/after test or reproduction steps |
| Refactor | `git diff` showing no behavior change + tests pass |
| Doc update | `grep` showing no stale refs |
| Config change | Validation output or runtime check |
| New feature | End-to-end test or manual verification log |

**Why:** "Done" without evidence is just "stopped working on it." Evidence creates a persistent, verifiable record.

**Enforcement:** Conductor requires evidence pasted into the active task. No evidence = task not marked done.

---

## The Stop Rule

When you finish the Active Task:

```
1. RUN tests
2. RUN drift guard again — did you create new drift?
3. UPDATE Conductor — mark done, paste evidence
4. STOP — if no next task is Ready, wait for human
```

**Why:** Prevents agents from picking the next task without human approval. Prevents drift from accumulating across sessions.

**Enforcement:** Session protocol. Agent must verify no new drift before declaring done.

---

## The No-Recreation Rule

If you think "I should build X":

1. Grep for X in the codebase
2. Check `docs/digests/index.md` for existing digests
3. Check the directory structure — does it already exist under a different name?
4. Check `AGENTS.md` — is there a "What Already Exists" entry?

**If X exists in any form, use it. Do not recreate.**

**Why:** Recreation is the #1 source of bloat. Every recreated function is technical debt.

**Enforcement:** Golden Rule + AGENTS.md "What Already Exists" table.

---

## The Contract Test Rule

If a change touches data crossing a function, file, thread, process, or persisted-state boundary, add or run a contract test.

Examples:
- JSON save/load round-trips
- API request/response schema validation
- Config parsing edge cases
- Database migration up/down

**Why:** Process docs prevent reinvention. Contract tests prevent regression.

**Enforcement:** Evidence rule requires test output for boundary-crossing changes.

---

## The Drift Score Rule

| Score | Meaning | Action |
|---|---|---|
| 90–100 | Clean | Proceed |
| 70–89 | Minor drift | Note in Conductor, proceed with caution |
| 50–69 | Moderate drift | Fix drift before adding new work |
| 0–49 | Severe drift | STOP. Fix drift first. |

**Why:** Quantifies documentation health. Gives agents a clear signal about whether the project is safe to modify.

**Enforcement:** `drifter check --score`. Pre-flight fails if score is below threshold.

---

## The Digest Rule

Every session produces a digest. Even a "small" session.

1. Write to `docs/digests/session-YYYY-MM-DD-brief-description.md`
2. Include: what you did, what you found, what you decided
3. Update `docs/digests/index.md` with the new digest
4. Cross-reference from the Conductor

**If you didn't write a digest, the session didn't happen.**

**Why:** Digests are the agent's memory. Without them, every session starts from zero.

**Enforcement:** Session protocol. Conductor tracks digest production.

---

## The Conductor Authority Rule

If the Conductor says:
- **Phase X is ACTIVE** → you work only on Phase X tasks
- **Task Y is blocked** → you do not start Task Y
- **Task Z is completed** → you do not revisit Task Z

The Conductor exists to prevent exactly the drift that happens when an agent goes deep on a file and forgets the big picture.

**Why:** Agents have no instinct for project-level prioritization. The conductor provides it.

**Enforcement:** Pre-flight step 3. Session protocol hard rules.

---

## The Document Type Rule

Every markdown file in `docs/` MUST have a `type:` in its frontmatter. Valid types:

| Type | Mutation Rule | Example |
|------|--------------|---------|
| `constitution` | Rarely changes. Amend, don't rewrite. | `methodology.md` |
| `snapshot` | Rewrite to reflect current truth. Never append. | `docs/architecture.md` |
| `backlog` | Open work only. Remove items when done. | `project-conductor.md` |
| `archive` | Append completed work. Never rewrite history. | `docs/archive/` |
| `playbook` | Update when process changes. | `AGENTS.md` |
| `guide` | Update when workflow changes. | `adoption-guide.md` |
| `reference` | Update when facts change. | `rules-reference.md` |

**Why:** Prevents documents from becoming lies. A snapshot that is appended to is no longer a snapshot.

**Enforcement:** `drifter validate` command.

---

## The Future State Lockout Rule

The following items are tracked for reference but are **out of scope** for all agent work unless explicitly approved:

- Experimental features not yet validated
- Major rewrites of working systems
- New dependencies not in the approved list
- Architecture changes not in the current phase

**Why:** Prevents agents from spending sessions on speculative work while real tasks stall.

**Enforcement:** Conductor "Blocked Tasks" section. AGENTS.md "Future Work" table.

---

## The Architecture Change Protocol

When changing project structure (renames, moves, new modules, dependency changes):

1. Update code
2. Update tests
3. Update config
4. Update ALL active docs (not just one)
5. Regenerate diagrams
6. Run cross-doc consistency verification (`drifter check`)

**Why:** Structural changes create the worst drift. A renamed file breaks every reference.

**Enforcement:** Evidence rule. Drift guard catches stale references.

---

## The Communication Rule

When reporting to humans:

1. **Lead with the answer, not the process.**
2. **Classify errors:** CODE / INFRASTRUCTURE / CONFIG / EXTERNAL
3. **If you don't know, say so.** Never hallucinate file contents.
4. **If you recreated something, admit it.**
5. **Update digests.** Every session produces a digest.

**Why:** Respects human time. Creates accountability.

**Enforcement:** AGENTS.md communication protocol section.

---

## The Dangerous Patterns Rule

> **Before running ANY shell command, read `dangerous_patterns.toml` at repo root.**

This file is the **canonical enforcement spec** for command restrictions. It is agent-agnostic: any AI agent can read it and know the boundaries.

**Classifications:**

| Type | Action | Example |
|------|--------|---------|
| `always_block` | ❌ NEVER run | `git commit`, `git push` |
| `blocked` | ❌ NEVER run | `rm -rf /`, `curl | sh` |
| `approval_required` | ⚠️ Ask human first | `git add` |
| `confirm_required` | ⚠️ Confirm with human | `sudo`, `rm -rf` |
| `allowed` | ✅ Proceed | `git status`, `git diff` |

**Why:** Prompts are suggestions; this file is enforceable. If the computer resets, clone the repo and read this file — you immediately know what commands are forbidden.

**Enforcement:**
- `ShellGuard.classify(command)` returns the classification
- `drifter check` verifies the file exists and is referenced in AGENTS.md
- `drifter audit` scans session history for violations

---

## The Git Boundary Rule

> **Agents NEVER run `git commit`, `git push`, `git reset`, `git rebase`, `git merge`, `git checkout -b`, `git tag`, `git cherry-pick`, or any history-mutating command.**

| Command | Allowed? | Condition |
|---------|----------|-----------|
| `git status`, `git diff`, `git log` | ✅ Yes | Informational only |
| `git add` | ⚠️ Only if explicitly asked | Never assume |
| `git commit`, `git push` | ❌ NEVER | Human's job |
| `git reset`, `git rebase`, `git merge` | ❌ NEVER | History-mutating |
| `git checkout -b`, `git tag`, `git cherry-pick` | ❌ NEVER | History-mutating |

**Why:**
- Agents don't understand release semantics (is this a patch? minor? major?)
- Agents can't write commit messages that capture human intent
- Agents may force-push or rewrite shared history without realizing consequences
- Human review of the diff before commit is a critical safety layer
- The Git Panel is the human's tool, not the agent's

**Prior approval does not roll forward.** If the human approved a `git commit` yesterday, you still need fresh approval today. Each git mutation is a separate decision.

**Enforcement:** AGENTS.md hard rule. Drift guard `GitSafetyCheck` scans source files for git mutation commands.

---

## Rule Summary Table

| Rule | Prevents | Enforced By |
|------|----------|-------------|
| Golden Rule | Recreation | Pre-flight step 6 |
| 7-Step Pre-Flight | Context blindness | `drifter preflight` |
| Scope Boundary | Bloat, rabbit holes | Session protocol |
| Evidence | False "done" claims | Conductor update requirement |
| Stop Rule | Drift accumulation | Session protocol |
| Git Boundary | History corruption, bad releases | AGENTS.md + drift guard |
| No-Recreation | Bloat | Golden Rule + AGENTS.md |
| Contract Test | Regression | Evidence rule |
| Drift Score | Unaware drift | `drifter check --score` |
| Digest | Memory loss | Session protocol |
| Conductor Authority | Wrong priorities | Pre-flight step 3 |
| Document Type | Doc-code drift | `drifter validate` |
| Future State Lockout | Speculative work | Conductor + AGENTS.md |
| Architecture Change | Structural drift | Evidence + drift guard |
| Communication | Human frustration | AGENTS.md protocol |

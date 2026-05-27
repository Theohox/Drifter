---
title: Session Protocol — Hard Rules for Every Session
type: playbook
status: active
phase: 1
created: '2026-05-27T00:00:00Z'
updated: '2026-05-27T23:03:16Z'
---

# Session Protocol — Hard Rules for Every Session

These rules are non-negotiable. Break them and you create drift.

---

## The 7-Step Pre-Flight (MUST DO)

Every session starts with this exact sequence:

```
1. READ  AGENTS.md                    — the agent contract
2. READ  docs/session-protocol.md     — this file. rules haven't changed.
3. READ  docs/project-conductor.md    — what phase? what's active?
4. RUN   drifter check                — what's the current drift?
5. PICK  one Active Task from the Conductor
6. GREP  for existing code before writing new code
7. READ  dangerous_patterns.toml     — command boundaries before running shell
```

No exceptions. No "I'll just quickly fix this one thing." Read the Conductor first.

---

## The Scope Boundary Rule

Before touching any file, declare:

> "I will only touch **[file]** for **[reason]**. I will not touch [related files]."

If you discover a related issue while working:
- Add it to Blocked Tasks in the Conductor
- Do NOT fix it immediately
- Finish your scoped task first

---

## The Evidence Rule

Every "done" task must have evidence:

| Task Type | Required Evidence |
|---|---|
| Code change | Test output showing pass |
| Bug fix | Test showing before/after |
| Refactor | `git diff` + test pass |
| Doc update | `grep` showing no stale refs |
| New check | Test proving it detects the drift class |
| Template change | Rendered output showing correct structure |

No evidence = not done.

---

## The Stop Rule

When you finish the Active Task:

```
1. RUN tests (pytest or relevant verification)
2. RUN drifter check again — did you create new drift?
3. UPDATE Conductor — mark done, paste evidence
4. STOP — if no next task is Ready, wait for human
```

Do not pick the next task yourself unless the Conductor explicitly lists it as "Ready."

---

## The Dangerous Patterns Rule

**Before running ANY shell command, read `dangerous_patterns.toml` at repo root.**

This file is the canonical enforcement spec. It tells you exactly what is forbidden, what requires approval, and what is safe.

| Classification | Action |
|----------------|--------|
| `always_block` / `blocked` | ❌ NEVER run |
| `approval_required` | ⚠️ Ask human first |
| `confirm_required` | ⚠️ Confirm with human |
| `allowed` | ✅ Proceed |

**If the file does not exist, STOP and create it.** It is as critical as this protocol.

---

## The Git Boundary Rule

**Agents NEVER mutate git history.**

| Command | Allowed? |
|---------|----------|
| `git status`, `git diff`, `git log` | ✅ Informational only |
| `git add` | ⚠️ Only if human explicitly asks |
| `git commit`, `git push`, `git reset`, `git rebase`, `git merge`, `git checkout -b`, `git tag`, `git cherry-pick` | ❌ NEVER |

**Prior approval does not roll forward.** Each git mutation requires fresh explicit approval.

**Enforcement:** Drifter detects violations automatically:
- `AgentSelfAuditCheck` — scans your bash history for blocked commands
- `GitCommitApprovalCheck` — verifies every commit has an approval marker (`[APPROVED BY ...]`)

**If you committed without approval, `drifter check` will fail.** Stop working. Report the violation. Do not commit again until the human approves.

The human reviews changes in the Git Panel and decides when to commit/push.

---

## The No-Recreation Rule

If you think "I should build X":

1. Grep for X in the codebase
2. Check `docs/digests/index.md` for existing digests
3. Check `src/` — does it already exist under a different name?
4. Check `AGENTS.md` — is there a "What Already Exists" entry?

**If X exists in any form, use it. Do not recreate.**

---

## The Drift Score Rule

| Score | Meaning | Action |
|---|---|---|
| 90–100 | Clean | Proceed |
| 70–89 | Minor drift | Note in Conductor, proceed with caution |
| 50–69 | Moderate drift | Fix drift before adding new work |
| 0–49 | Severe drift | STOP. Fix drift first. |

If Drifter reports errors, you must fix them before declaring the session complete.

---

## The Digest Rule

Every session produces a digest. Even a "small" session.

1. Write to `docs/digests/session-YYYY-MM-DD-brief-description.md`
2. Include: what you did, what you found, what you decided
3. Update `docs/digests/index.md` with the new digest
4. Cross-reference from the Conductor

If you didn't write a digest, the session didn't happen.

---

## The Conductor Is The Boss

If the Conductor says:
- **Phase X is ACTIVE** → you work only on Phase X tasks
- **Task Y is blocked** → you do not start Task Y
- **Task Z is completed** → you do not revisit Task Z

The Conductor exists to prevent exactly the drift that happens when an agent goes deep on a file and forgets the big picture.

---

## Emergency Override

If you find a **critical bug** (tests failing, system won't boot, data loss risk):

1. Fix the bug immediately
2. Add it to Conductor as "Emergency Fix"
3. Write a digest explaining the bug and fix
4. Update the Conductor's Active Task to resume

Critical bugs override the normal flow. Everything else waits.

---

## Communication Protocol

**When reporting to humans:**

1. **Lead with the answer, not the process.**
2. **Classify errors:** CODE / INFRASTRUCTURE / CONFIG / EXTERNAL
3. **If you don't know, say so.** Never hallucinate file contents.
4. **If you recreated something, admit it.**
5. **Update digests.** Every session produces a digest.

---

*This protocol exists because without it, agents drift. Drift = documented features that don't exist, stale references, forgotten tasks, and duplicated code. Follow the protocol. Update the Conductor. Stay honest.*

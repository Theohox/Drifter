---
title: Drifter Methodology — The Philosophy and Why
type: constitution
status: active
created: '2026-05-27T00:00:00Z'
updated: '2026-05-27T00:00:00Z'
---

# Drifter Methodology — The Philosophy and Why

This document explains why Drifter exists, what problems it solves, and why each rule is structured the way it is. Read this before adopting Drifter in a project.

---

## The Four Failure Modes of AI Agents

After running AI agents across multiple production codebases for months, we observed four recurring failure modes. They are not bugs in the agent — they are structural consequences of how agents interact with code.

### 1. Hallucination

**What it looks like:** An agent invents a file that doesn't exist, references a function that was never written, or proposes an API that was never designed. It then builds code around this hallucination, creating a cascade of phantom dependencies.

**Why it happens:**
- Agents have no persistent memory of prior sessions
- Context windows truncate, and agents fill gaps with plausible-sounding fiction
- Agents are optimized to be helpful, and "I don't know" is penalized by training

**Why traditional fixes fail:**
- "Please don't hallucinate" in a system prompt is ignored under pressure
- Longer prompts just get truncated
- Chain-of-thought reasoning can actually make hallucinations more coherent and harder to detect

**Drifter's solution:** The **No-Recreation Rule** + **Pre-Flight Protocol**. Before writing code, the agent must grep the codebase and read the conductor. The evidence rule requires test output, which fails if the underlying assumption was hallucinated.

### 2. Bloat

**What it looks like:** A 50-line script becomes a 500-line module with configuration systems, plugin architectures, and abstraction layers that will never be used. Every agent session adds a new layer because it's easier to add than to understand.

**Why it happens:**
- Agents are trained on open-source code, which tends toward generality
- Agents don't feel the maintenance burden of their abstractions
- "Refactor" is safer for an agent than "delete" — deletion requires understanding, refactoring just requires pattern-matching

**Why traditional fixes fail:**
- "Keep it simple" is subjective
- Agents interpret "simple" as "use a well-known design pattern," which often adds indirection
- Code review by humans happens after the bloat is written

**Drifter's solution:** The **Scope Boundary Rule** + **Document Type System**. The agent must declare exactly what files it will touch and why. The conductor tracks one active task at a time, preventing scope creep. Constitution-type documents encode the project's actual complexity budget.

### 3. Context Blindness

**What it looks like:** An agent edits a function without reading its callers, adds a parameter without updating all call sites, or implements a feature that already exists three directories away under a different name.

**Why it happens:**
- Agents see the files you open, not the files that matter
- Grepping is unreliable — agents often grep for what they expect to find
- File explorers and directory listings are too large to fit in context

**Why traditional fixes fail:**
- "Please read the whole codebase first" is impossible for large projects
- Static analysis tools exist but are not integrated into agent workflows
- Agents don't know what they don't know

**Drifter's solution:** The **Golden Rule** (grep before you write) + **Drift Guard** (automated cross-reference checking). The drift guard scans docs for stale file references and code for hardcoded paths, catching the symptoms of context blindness before they compound.

### 4. Drift

**What it looks like:** Docs say one thing, code does another. A README describes a 3-step process that now takes 7 steps. An architecture diagram shows components that were deleted months ago. A "current state" document describes a system that no longer exists.

**Why it happens:**
- Agents update code but not docs, or docs but not code
- Documents accumulate append-only history and become unreadable
- No one owns documentation freshness

**Why traditional fixes fail:**
- "Update the docs" is the last item on every checklist, and the first to be skipped
- Documentation is not tested, so drift is invisible until a human reads it
- Different docs have different update cadences, but agents treat them all the same

**Drifter's solution:** The **Document Type System** + **Drift Guard**. Every document has a type that dictates how it mutates. Snapshots must be rewritten, not appended. Backlogs must have items removed when done. The drift guard automatically detects stale references and doc-code divergence.

---

## Why Reactive Prompting Fails

Most attempts to control AI agents use **reactive prompting**: longer system prompts, more detailed instructions, "please remember to..." caveats. This fails for three structural reasons.

### Reason 1: Prompts Are Suggestions, Not Enforcement

An agent can ignore any part of a prompt. There is no mechanism to ensure compliance. When the agent is under pressure (a complex task, a long conversation, a tight context window), it drops the parts of the prompt that feel like "overhead" and keeps the parts that feel like "the real work."

### Reason 2: Prompts Don't Compose

A 500-word prompt works. A 5,000-word prompt gets truncated. A 50,000-word prompt is impossible. As projects grow, the amount of context an agent needs grows too. You cannot scale reactive prompting.

### Reason 3: Prompts Are Ephemeral

A prompt exists for one session. The next session starts from zero. Agents don't remember that they broke a rule last time, or that a particular check caught a bug. Every session is a new chance to make the same mistake.

---

## Why Proactive Enforcement Works

Drifter uses **proactive enforcement**: scripts, structure, and protocols that run before the agent writes code. These work because they change the agent's environment, not the agent's instructions.

### Enforcement 1: The Pre-Flight Protocol

The 6-step pre-flight is a **gate**, not a suggestion. The agent cannot proceed to coding until it has:
1. Read the contract
2. Read the rules
3. Read the conductor
4. Run the drift guard
5. Picked a task
6. Searched for existing code

This is enforced by the `drifter preflight` command, which returns a non-zero exit code if any step fails. Agents that integrate Drifter run this command automatically at session start.

### Enforcement 2: The Document Type System

Documents have types with **mutation rules**. A snapshot-type document that has been appended to instead of rewritten is a detectable violation. A backlog that still contains completed items is a detectable violation. The `drifter validate` command catches these automatically.

This works because it externalizes the rules. The agent doesn't need to remember "don't append to current_state.md" — the validator enforces it.

### Enforcement 3: The Drift Guard

The drift guard is a **static analysis tool** for documentation. It scans markdown files for file references and verifies they exist. It scans source code for hardcoded paths and verifies they exist. It checks digests for stale pending items. It verifies the conductor has exactly one active task.

This works because it runs independently of the agent. Even if the agent forgets to check, the CI pipeline catches it.

### Enforcement 4: The Project Conductor

The conductor is a **single source of truth** for project state. It answers: what phase are we in? What's the active task? What's blocked? What's done?

This works because it removes ambiguity. An agent that knows exactly what task is active is less likely to wander. An agent that must update the conductor before declaring "done" is less likely to skip verification.

---

## The Evidence Rule: Why "Done" Requires Proof

The most common lie an agent tells is "this is done." Without the evidence rule, "done" means "the agent stopped working on it." With the evidence rule, "done" means "there is verifiable proof that the change works and doesn't break anything."

| Claim | Without Evidence Rule | With Evidence Rule |
|-------|----------------------|-------------------|
| "I fixed the bug" | Agent moves on | Agent pastes test output showing the bug is fixed |
| "I updated the docs" | Agent moves on | Agent greps to show no stale references remain |
| "I added a new check" | Agent moves on | Agent shows the check detects its target drift class |
| "The tests pass" | Agent asserts it | Agent pastes pytest output |

The evidence rule is not about distrust. It is about **verifiability**. In a system where agents start from zero every session, the only persistent record of what happened is the evidence left behind.

---

## The Architecture Change Protocol

When an agent changes the structure of a project (renames a component, moves files, adds a new module), it must update every artifact that references that structure. This is the **Architecture Change Protocol**.

Why? Because structural changes create the worst kind of drift. A renamed file breaks every doc that referenced it. A moved module breaks every import. A new dependency changes the setup instructions. If the agent only updates the code, the docs become lies.

The protocol is a checklist. For any structural change:
- [ ] Code updated
- [ ] Tests updated
- [ ] Config updated
- [ ] Docs updated (all active docs, not just one)
- [ ] Diagrams regenerated
- [ ] Cross-doc consistency verified

Drifter automates the last step. `drifter check` scans for stale references after any change.

---

## Why Document Types Matter

Not all documents serve the same purpose. Treating them the same causes drift.

A **snapshot** (`current_state.md`) tells you what the system looks like *right now*. If you append to it, it becomes a history document, and no one knows what the current state is.

A **backlog** (`agent_open.md`) tells you what work is *not done*. If you leave completed items in it, it becomes a history document, and no one knows what's actually open.

An **archive** (`agent_closed.md`) tells you what work *was done* and *why*. If you rewrite it, you lose the historical context that prevents recreation.

A **constitution** (`Purpose.md`) tells you what the system *is* and *is not*. If you change it frequently, it becomes a changelog, and no one knows what the stable principles are.

The document type system encodes these rules explicitly. It is not bureaucracy — it is a **state machine for documentation**. Each type has valid transitions, and invalid transitions are drift.

---

## Relationship to Memory

Drifter solves **discipline**: enforced protocols that prevent agents from making structural mistakes. It does not solve **memory**: the ability for an agent to remember what happened in prior sessions.

For memory, we recommend complementary tools like [claude-mem](https://github.com/thedotmack/claude-mem) or project-specific digest systems. Drifter's document type system and digest rules are designed to work with these tools — a digest is a snapshot-type document that captures session context for future sessions.

The distinction:
- **Discipline** = "Don't make this mistake in the first place"
- **Memory** = "Remember that you made this mistake before"

Both are necessary. Neither is sufficient alone.

---

## Why Agents Must Not Touch Git History

The Git Boundary Rule exists because git history is not just code — it is a **communication layer** between humans. Agents that mutate git history destroy that layer.

### Release Semantics
Agents don't know whether a change is a patch fix, a minor feature, or a breaking change. They don't know if the codebase is in a release freeze. They don't know if `main` is protected. A `git push` from an agent can trigger CI deployments, notify stakeholders, or break downstream consumers — all without the human realizing it happened.

### Commit Messages Are Intent Documentation
A good commit message explains *why* a change was made, not just *what* changed. Agents can describe what they did, but they cannot capture the human intent behind the change. Commits written by agents become archaeological noise — future developers read them and learn nothing.

### History Rewriting Is Invisible to Agents
An agent that runs `git rebase -i` or `git push --force` may not understand that it just erased a colleague's work. Agents lack the social context to know that force-push at 3pm on a Friday is different from force-push on a feature branch no one else has checked out.

### The Git Panel Is the Human's Review Surface
Modern IDEs and editors provide a Git Panel where humans review diffs, stage hunks, and write commits. This is a **deliberate review surface**. Bypassing it means bypassing the last human check before code enters the permanent record.

### The One Exception: `git add`
Staging files (`git add`) is sometimes necessary for the agent to show the human what changed. But even this requires explicit permission. The agent should never assume staging is desired.

---

## Adoption Criteria

Drifter is not for every project. It adds overhead. Adopt it when:

- The project has ≥2 agents working on it (or 1 agent across many sessions)
- The project has documentation that must stay accurate
- The project has a history of recreation, bloat, or drift
- The project has a maintenance phase, not just a build phase

Do not adopt Drifter for:
- One-off scripts
- Rapid prototyping that will be thrown away
- Projects with no documentation
- Teams that will not enforce the pre-flight protocol

---

*This document is a constitution. It changes rarely. If you propose a change, explain which of the four failure modes it addresses and why the current approach fails.*

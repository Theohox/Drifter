---
title: Document Type System
type: reference
status: active
phase: 0
created: '2026-05-27T00:00:00Z'
updated: '2026-05-27T23:03:16Z'
---

# Document Type System

The document type system is the foundation of Drifter's drift prevention. Every markdown file in `docs/` (and `AGENTS.md` at the root) must declare its type in YAML frontmatter. The type dictates how the document may be mutated.

---

## Why Types Matter

Documents become lies when they are mutated in ways that violate their purpose:

- A **snapshot** that is appended to becomes a history document — no one knows the current state
- A **backlog** that keeps completed items becomes a graveyard — no one knows what's actually open
- An **archive** that is rewritten loses the historical context that prevents recreation
- A **constitution** that changes weekly becomes a changelog — no one knows what the stable principles are

The document type system makes these violations **detectable**.

---

## Types

### `constitution`

**Purpose:** Stable principles that rarely change. The "why" of the project.

**Examples:**
- `docs/methodology.md` — why Drifter exists and what problems it solves
- `AGENTS.md` — what the system is and is not

**Mutation Rules:**
- Amend, don't rewrite. Additions should be rare and justified.
- If a principle changes, the old principle should be explicitly deprecated, not silently replaced.
- Update the `updated:` timestamp when amended.

**Drift Signals:**
- Frequent changes (more than once per month)
- Rewrites that remove historical context
- Contradictions with other constitution documents

---

### `snapshot`

**Purpose:** Current truth. What the system looks like *right now*.

**Examples:**
- `docs/architecture.md` — current system architecture and component inventory

**Mutation Rules:**
- **Rewrite, don't append.** The entire document should be rewritten to reflect current truth.
- No historical notes. Historical context belongs in archive-type documents.
- Update the `updated:` timestamp on every change.

**Drift Signals:**
- Append-only growth (document gets longer over time)
- Stale `updated:` timestamp
- References to components that no longer exist
- Numbers that don't match reality

---

### `backlog`

**Purpose:** Open work only. What needs to be done.

**Examples:**
- `docs/project-conductor.md` — active task tracker (the "Active Task" and "Blocked Tasks" sections)

**Mutation Rules:**
- **Remove items when done.** Do not strikethrough and keep.
- Completed work moves to an archive-type document.
- Update the `updated:` timestamp when tasks change status.

**Drift Signals:**
- Completed items still present
- Stale `updated:` timestamp
- Active task with no evidence
- Multiple active tasks

---

### `archive`

**Purpose:** Completed work with context. What was done and why.

**Examples:**
- `docs/archive/` — completed tasks with evidence and context
- `docs/digests/session-*.md` — session notes

**Mutation Rules:**
- **Append only.** Never rewrite historical entries.
- Each entry should include: what was done, why, and verification.
- Update the `updated:` timestamp when appending.

**Drift Signals:**
- Rewritten entries (historical context lost)
- Missing verification for claimed completions

---

### `playbook`

**Purpose:** Operational procedures. How agents should work.

**Examples:**
- `AGENTS.md` — the canonical agent contract
- `docs/session-protocol.md` — hard rules for every session

**Mutation Rules:**
- Update when process changes.
- Keep concise. If it grows beyond 300 lines, split into multiple playbooks.
- Update the `updated:` timestamp when changed.

**Drift Signals:**
- References to procedures that no longer exist
- Instructions that contradict the codebase
- Stale `updated:` timestamp

---

### `guide`

**Purpose:** How-to documentation for humans or agents.

**Examples:**
- `docs/adoption-guide.md` — how to adopt Drifter
- `docs/methodology.md` — philosophy and design principles

**Mutation Rules:**
- Update when workflow changes.
- Step-by-step instructions should be tested before publishing.
- Update the `updated:` timestamp when changed.

**Drift Signals:**
- Instructions that don't work
- References to files or commands that have changed

---

### `reference`

**Purpose:** Lookup documentation. Facts, APIs, catalogs.

**Examples:**
- `docs/rules-reference.md` — complete rule catalog
- `docs/phase-index.md` — maps all docs to their phase

**Mutation Rules:**
- Update when facts change.
- Should be comprehensive and searchable.
- Update the `updated:` timestamp when changed.

**Drift Signals:**
- Facts that contradict the codebase
- Missing entries for new features

---

## Frontmatter Schema

Every typed document must include:

```yaml
---
title: Human-readable title
type: <constitution|snapshot|backlog|archive|playbook|guide|reference|index>
status: <active|draft|archived|deprecated>
created: 'YYYY-MM-DDTHH:MM:SSZ'
updated: 'YYYY-MM-DDTHH:MM:SSZ'
---
```

### Required Fields

| Field | Description |
|-------|-------------|
| `title` | Human-readable title |
| `type` | One of the types above |
| `status` | `active`, `draft`, `archived`, or `deprecated` |
| `created` | ISO 8601 timestamp |
| `updated` | ISO 8601 timestamp, must be updated on every mutation |

### Optional Fields

| Field | Description |
|-------|-------------|
| `tags` | List of tags for categorization |
| `related` | List of related document paths |
| `author` | Document owner |

---

## Validation

Run `drifter validate` to check:

1. Every `.md` file in `docs/` has a `type:` field
2. The `type:` value is valid
3. The `updated:` timestamp is present and not older than the `created:` timestamp
4. Snapshot-type documents have not grown excessively (warning if >2× original length)
5. Backlog-type documents don't contain stale items (checked by drift guard)

---

## Migration Guide

If your project already has documentation without types:

1. Run `drifter validate` to get a list of untyped documents
2. For each document, decide its type based on its purpose
3. Add frontmatter with the correct type
4. Run `drifter validate` again
5. Fix any structural issues (missing timestamps, invalid types)

Start with the most important documents:
1. `AGENTS.md` or equivalent → `playbook`
2. `README.md` → `guide` (or leave untyped if it's purely human-facing)
3. Current state document → `snapshot`
4. Task tracker → `backlog`
5. Session notes → `archive`

---

*This document is a reference. Update it when new document types are added.*

---
title: Phase Index — Documents by Phase
type: index
status: active
phase: 1
created: '2026-05-27T00:00:00Z'
updated: '2026-05-27T23:03:16Z'
---

# Phase Index — Documents by Phase

This index maps every document to its originating phase. Documents are **not moved** into phase folders — they live at `docs/` root and declare their phase in frontmatter. This prevents broken links while preserving phase history.

---

## Phase 0: Foundation

Documents created during the foundation phase. These are stable and rarely change.

| Document | Type | Status | Description |
|----------|------|--------|-------------|
| [Methodology](methodology.md) | constitution | active | The "why" — philosophy and design principles |
| [Adoption Guide](adoption-guide.md) | guide | active | Step-by-step for any project |
| [Rules Reference](rules-reference.md) | reference | active | Complete rule catalog |
| [Document Types](document-types.md) | reference | active | Type system for docs |
| [Architecture](architecture.md) | snapshot | active | Internal architecture |

---

## Phase 1: Polish & Dogfooding

Documents created or significantly updated during the polish phase. These are living documents.

| Document | Type | Status | Description |
|----------|------|--------|-------------|
| [Session Protocol](session-protocol.md) | playbook | active | Hard rules for every session |
| [Project Conductor](project-conductor.md) | backlog | active | Active task tracker |
| [Phase Index](phase-index.md) | index | active | This file — maps docs to phases |

---

## Cross-Phase (No Phase Declared)

Documents that span all phases or are not tied to a specific phase.

| Document | Location | Description |
|----------|----------|-------------|
| README.md | repo root | Quick start and overview |
| AGENTS.md | repo root | Agent contract — read every session |
| Digest Index | [digests/index.md](digests/index.md) | Session digest directory |

---

## How to Update This Index

When a new document is added:

1. Add `phase: N` to its frontmatter
2. Add it to the appropriate section above
3. Run `drifter check` — the phase index is a document too

When a document's phase changes (rare):
1. Update its `phase:` frontmatter
2. Move it to the correct section above
3. Update any docs that reference it

---

*This index exists so you can answer "What did we build in Phase 0?" without grepping the entire docs directory.*

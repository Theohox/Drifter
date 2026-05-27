"""Conductor helper functions — extracted from conductor.py."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug[:50]


def create_archive_file(
    root: Path, task_id: str, task_name: str, evidence: str, phase: str = "0"
) -> Path | None:
    archive_dir = root / "docs" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(task_name)
    archive_path = archive_dir / f"{task_id}-{slug}.md"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content = f"""---
title: "{task_id}: {task_name}"
type: archive
status: archived
phase: {phase}
created: '{now}'
completed: '{now}'
score: 100
task_id: {task_id}
---

# {task_id}: {task_name}

## Evidence

{evidence}

## Decisions

- (Auto-generated — add key decisions here)

## Files Changed

- (Auto-generated — list changed files here)

## Related Tasks

- Depends on: —
- Leads to: —
"""
    archive_path.write_text(content, encoding="utf-8")
    return archive_path


def default_conductor_content() -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"""---
title: Project Conductor — Master Plan & Active Task Tracker
type: backlog
status: active
created: '{now}'
updated: '{now}'
---

# Project Conductor — Master Plan & Active Task Tracker

**This is the single source of truth for what we're doing, what's blocked, and what's done.**

> Read this BEFORE every session. Pick the ONE active task. Do it. Verify it. Update this file. Stop.

---

## Current Phase

**Phase 0: Foundation** 🟢 ACTIVE

**Goal**: Establish project structure and baseline.

**Exit Criteria**:
- [ ] Project structure in place
- [ ] Core documentation written
- [ ] Drift guard runs clean

---

## Active Task

| Field | Value |
|-------|-------|
| **ID** | 0.1 |
| **Name** | Initialize project |
| **Status** | 🟡 IN PROGRESS |
| **Evidence** | — |
| **Next** | 0.2: First drift guard check |

---

## Blocked Tasks

| ID | Name | Blocked On | ETA |
|----|------|-----------|-----|
| — | — | — | — |

---

## Future Tasks

| ID | Name | Status | Docs |
|----|------|--------|------|
| — | — | — | — |

---

## How to Update This File

When you finish the Active Task:

1. **Paste evidence** into the Active Task table
2. **Update Phase Status** if phase is complete
3. **Run Drift Guard** — did you create new drift?
4. **STOP** — if no next task is Ready, wait for human

---

## Drift Score History

| Timestamp | Score | Tests | Notes |
|-----------|-------|-------|-------|
| — | — | — | — |

---

*This file is the captain's log. If it's not updated, the ship drifts.*
"""

"""Conductor manager — CLI utilities for managing project conductor state."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from drifter.config import Config


@dataclass
class Task:
    id: str
    name: str
    status: str
    evidence: str
    next_task: str | None = None


class Conductor:
    """Manager for the project conductor file."""

    def __init__(self, root: Path | None = None, config: Config | None = None):
        if config is None:
            config = Config.load(root)
        self.config = config
        self.root = config.root
        self.path = self.root / "docs" / "project-conductor.md"
        if not self.path.exists():
            self.path = self.root / "project-conductor.md"

    def exists(self) -> bool:
        return self.path.exists()

    def read(self) -> str:
        if not self.exists():
            return ""
        return self.path.read_text(encoding="utf-8")

    def show(self) -> dict[str, Any]:
        """Pretty-print the active task and phase."""
        text = self.read()
        if not text:
            return {"error": "Conductor file not found"}

        # Extract phase
        phase_match = re.search(r"\*\*Phase[^*]+\*\*.*?(🟢|🟡|🔴|🔄)\s*ACTIVE", text)
        phase = phase_match.group(0) if phase_match else "Unknown"

        # Extract active task
        task_match = re.search(
            r"\*\*ID\*\*\s*\|\s*(.+?)\n.*?\*\*Name\*\*\s*\|\s*(.+?)\n.*?\*\*Status\*\*\s*\|\s*(.+?)\n.*?\*\*Evidence\*\*\s*\|\s*(.+?)\n",
            text,
            re.DOTALL,
        )
        task = None
        if task_match:
            task = {
                "id": task_match.group(1).strip(),
                "name": task_match.group(2).strip(),
                "status": task_match.group(3).strip(),
                "evidence": task_match.group(4).strip(),
            }

        return {
            "phase": phase,
            "active_task": task,
            "file": str(self.path.relative_to(self.root)),
        }

    def mark_done(self, task_id: str, evidence: str) -> bool:
        """Mark a task as done with evidence."""
        if not self.exists():
            return False

        text = self.read()

        # Find the active task section and update status + evidence
        # This is a best-effort regex replacement
        old_pattern = re.compile(
            r"(\*\*Status\*\*\s*\|\s*)(.+?)(\n.*?\*\*Evidence\*\*\s*\|\s*)(.*?)(\n)",
            re.DOTALL,
        )

        def replacer(m: re.Match[str]) -> str:
            return f"{m.group(1)}✅ COMPLETE{m.group(3)}{evidence}{m.group(5)}"

        new_text, count = old_pattern.subn(replacer, text, count=1)
        if count == 0:
            return False

        # Update the updated timestamp
        new_text = self._update_timestamp(new_text)

        self.path.write_text(new_text, encoding="utf-8")
        return True

    def block_task(self, task_id: str, reason: str) -> bool:
        """Add a task to the blocked tasks section."""
        if not self.exists():
            return False

        text = self.read()

        # Find Blocked Tasks section and append
        blocked_section = re.search(r"(## Blocked Tasks.*?\n)(\|?-+\|?-+.*?\n)(.*?)(?=##|$)", text, re.DOTALL)
        if not blocked_section:
            return False

        # Append new row
        new_row = f"| {task_id} | {reason} | discovered during current task | — |\n"
        insert_pos = blocked_section.end(3)
        new_text = text[:insert_pos] + new_row + text[insert_pos:]
        new_text = self._update_timestamp(new_text)

        self.path.write_text(new_text, encoding="utf-8")
        return True

    def next_task(self) -> dict[str, Any]:
        """Show the next ready task from the conductor."""
        text = self.read()
        if not text:
            return {"error": "Conductor file not found"}

        # Look for future tasks or blocked tasks that might be unblocked
        # This is heuristic — the conductor is human-managed
        return {
            "message": "Check the conductor manually for the next ready task.",
            "hint": "Look for tasks in 'Future Tasks' or review 'Blocked Tasks'.",
        }

    def _update_timestamp(self, text: str) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        # Replace updated field in frontmatter
        updated_pattern = re.compile(r"(updated:\s*').*?(')")
        return updated_pattern.sub(rf"\g<1>{now}\g<2>", text, count=1)

    def init(self, force: bool = False) -> Path:
        """Create a new conductor from template."""
        if self.exists() and not force:
            return self.path

        template_path = Path(__file__).parent.parent / "templates" / "project-conductor.md.tmpl"
        if template_path.exists():
            content = template_path.read_text(encoding="utf-8")
        else:
            content = self._default_conductor()

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(content, encoding="utf-8")
        return self.path

    def _default_conductor(self) -> str:
        return """---
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
""".format(now=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

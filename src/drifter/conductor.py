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

    def _touch_timestamp(self) -> None:
        """Auto-update the conductor's 'updated:' timestamp to now."""
        if not self.exists():
            return
        text = self.read()
        new_text = self._update_timestamp(text)
        if new_text != text:
            self.path.write_text(new_text, encoding="utf-8")

    def append_drift_score(self, score: int, tests: int = 0, notes: str = "") -> None:
        """Append a drift score entry to the history table."""
        if not self.exists():
            return
        text = self.read()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        new_row = f"| {now} | {score}/100 | {tests} | {notes} |"

        lines = text.split("\n")
        in_history = False
        header_idx = -1
        last_data_idx = -1

        for i, line in enumerate(lines):
            if "## Drift Score History" in line:
                in_history = True
                header_idx = i
                continue
            if in_history:
                if line.strip().startswith("## "):
                    break
                if line.strip().startswith("|") and "Timestamp" not in line and "---" not in line:
                    if "—" not in line:
                        last_data_idx = i

        if header_idx < 0:
            return

        # Find the separator line (|---|) after the header
        sep_idx = -1
        for i in range(header_idx, min(last_data_idx + 2 if last_data_idx >= 0 else len(lines), len(lines))):
            if "|---" in lines[i] or "| -" in lines[i]:
                sep_idx = i
                break

        insert_idx = last_data_idx if last_data_idx >= 0 else sep_idx
        if insert_idx < 0:
            return

        # Insert after the last data row, or after separator if table was empty
        lines.insert(insert_idx + 1, new_row)

        new_text = "\n".join(lines)
        new_text = self._update_timestamp(new_text)
        self.path.write_text(new_text, encoding="utf-8")

    def show(self) -> dict[str, Any]:
        """Pretty-print the active task and phase."""
        self._touch_timestamp()
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

    def _slugify(self, text: str) -> str:
        """Convert text to a URL-friendly slug."""
        slug = re.sub(r"[^\w\s-]", "", text.lower())
        slug = re.sub(r"[-\s]+", "-", slug).strip("-")
        return slug[:50]

    def _create_archive_file(
        self,
        task_id: str,
        task_name: str,
        evidence: str,
        phase: str = "0",
    ) -> Path | None:
        """Create an archive file for a completed task."""
        archive_dir = self.root / "docs" / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)

        slug = self._slugify(task_name)
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

    def mark_done(self, task_id: str, evidence: str) -> bool:
        """Mark a task as done with evidence and archive it."""
        if not self.exists():
            return False

        text = self.read()

        # Extract active task fields for archiving
        task_match = re.search(
            r"\*\*ID\*\*\s*\|\s*(.+?)\n.*?\*\*Name\*\*\s*\|\s*(.+?)\n.*?\*\*Status\*\*\s*\|\s*(.+?)\n.*?\*\*Evidence\*\*\s*\|\s*(.+?)\n",
            text,
            re.DOTALL,
        )
        if not task_match:
            return False

        task_name = task_match.group(2).strip()

        # Extract phase from frontmatter
        phase_match = re.search(r"phase:\s*(\d+)", text)
        phase = phase_match.group(1) if phase_match else "0"

        # Create archive file
        archive_path = self._create_archive_file(task_id, task_name, evidence, phase)
        archive_rel = f"archive/{archive_path.name}" if archive_path else ""

        # Find the active task section and update status + evidence
        old_pattern = re.compile(
            r"(\*\*Status\*\*\s*\|\s*)(.+?)(\n.*?\*\*Evidence\*\*\s*\|\s*)(.*?)(\n)",
            re.DOTALL,
        )

        def replacer(m: re.Match[str]) -> str:
            return f"{m.group(1)}✅ COMPLETE{m.group(3)}{evidence}{m.group(5)}"

        new_text, count = old_pattern.subn(replacer, text, count=1)
        if count == 0:
            return False

        # Archive the completed task — link to archive file
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        archive_link = f"[archive]({archive_rel})" if archive_rel else evidence
        archive_row = f"| {task_id} | {task_name} | {now} | {archive_link} | — |"

        # Find Completed Tasks section and append
        lines = new_text.split("\n")
        in_completed = False
        header_idx = -1
        last_data_idx = -1

        for i, line in enumerate(lines):
            if "## Completed Tasks" in line:
                in_completed = True
                header_idx = i
                continue
            if in_completed:
                if line.strip().startswith("## "):
                    break
                if line.strip().startswith("|") and "ID" not in line and "---" not in line:
                    if "—" not in line:
                        last_data_idx = i

        if header_idx >= 0:
            sep_idx = -1
            for i in range(header_idx, min(last_data_idx + 2 if last_data_idx >= 0 else len(lines), len(lines))):
                if "|---" in lines[i] or "| -" in lines[i]:
                    sep_idx = i
                    break
            insert_idx = last_data_idx if last_data_idx >= 0 else sep_idx
            if insert_idx >= 0:
                lines.insert(insert_idx + 1, archive_row)
                new_text = "\n".join(lines)

        # Update the updated timestamp
        new_text = self._update_timestamp(new_text)

        self.path.write_text(new_text, encoding="utf-8")
        return True

    def block_task(self, task_id: str, reason: str) -> bool:
        """Add a task to the blocked tasks section."""
        if not self.exists():
            return False

        text = self.read()

        # Find Blocked Tasks section and append inside the table
        lines = text.split("\n")
        in_blocked = False
        header_idx = -1
        last_data_idx = -1

        for i, line in enumerate(lines):
            if "## Blocked Tasks" in line:
                in_blocked = True
                header_idx = i
                continue
            if in_blocked:
                if line.strip().startswith("## "):
                    break
                if line.strip().startswith("|") and "ID" not in line and "---" not in line:
                    if "—" not in line:
                        last_data_idx = i

        if header_idx < 0:
            return False

        sep_idx = -1
        for i in range(header_idx, min(last_data_idx + 2 if last_data_idx >= 0 else len(lines), len(lines))):
            if "|---" in lines[i] or "| -" in lines[i]:
                sep_idx = i
                break

        insert_idx = last_data_idx if last_data_idx >= 0 else sep_idx
        if insert_idx < 0:
            return False

        new_row = f"| {task_id} | {reason} | discovered during current task | — |"
        lines.insert(insert_idx + 1, new_row)
        new_text = "\n".join(lines)
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

        # Try src/ layout first (project root / templates), then fallback
        template_path = Path(__file__).parent.parent.parent / "templates" / "project-conductor.md.tmpl"
        if not template_path.exists():
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

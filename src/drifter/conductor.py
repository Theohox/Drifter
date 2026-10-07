"""Conductor manager — CLI utilities for managing project conductor state."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from drifter._conductor_helpers import create_archive_file, default_conductor_content
from drifter._templates import template_text
from drifter.config import Config


def _insert_table_row(
    lines: list[str], section_header: str, column_header: str, row: str
) -> bool:
    """Insert ``row`` at the end of the markdown table under ``section_header``.

    Mutates ``lines`` in place; returns True on success. Placeholder rows
    containing "—" don't count as data rows, so the new row lands after the
    last real data row or, failing that, right after the separator.
    """
    header_idx = -1
    last_data_idx = -1
    in_section = False
    for i, line in enumerate(lines):
        if section_header in line:
            in_section = True
            header_idx = i
            continue
        if in_section:
            if line.strip().startswith("## "):
                break
            if (
                line.strip().startswith("|")
                and column_header not in line
                and "---" not in line
                and "—" not in line
            ):
                last_data_idx = i
    if header_idx < 0:
        return False
    sep_idx = -1
    for i in range(
        header_idx,
        min(last_data_idx + 2 if last_data_idx >= 0 else len(lines), len(lines)),
    ):
        if "|---" in lines[i] or "| -" in lines[i]:
            sep_idx = i
            break
    insert_idx = last_data_idx if last_data_idx >= 0 else sep_idx
    if insert_idx < 0:
        return False
    lines.insert(insert_idx + 1, row)
    return True


def _latest_drift_score(text: str) -> int | None:
    """Return the most recent score from the Drift Score History table."""
    parts = text.split("## Drift Score History", 1)
    if len(parts) < 2:
        return None
    section = parts[1].split("\n## ", 1)[0]
    matches = re.findall(r"\|\s*(\d+)\s*/\s*100\s*\|", section)
    return int(matches[-1]) if matches else None


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
        if not self.exists():
            return
        text = self.read()
        new_text = self._update_timestamp(text)
        if new_text != text:
            self.path.write_text(new_text, encoding="utf-8")

    def append_drift_score(self, score: int, tests: int = 0, notes: str = "") -> None:
        if not self.exists():
            return
        text = self.read()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        new_row = f"| {now} | {score}/100 | {tests} | {notes} |"
        lines = text.split("\n")
        if not _insert_table_row(lines, "## Drift Score History", "Timestamp", new_row):
            return
        new_text = "\n".join(lines)
        new_text = self._update_timestamp(new_text)
        self.path.write_text(new_text, encoding="utf-8")

    def show(self) -> dict[str, Any]:
        self._touch_timestamp()
        text = self.read()
        if not text:
            return {"error": "Conductor file not found"}
        phase_match = re.search(r"\*\*Phase[^*]+\*\*.*?(🟢|🟡|🔴|🔄)\s*ACTIVE", text)
        phase = phase_match.group(0) if phase_match else "Unknown"
        task_match = re.search(
            r"\*\*ID\*\*\s*\|\s*([^|\n]+?)\s*\|.*?\*\*Name\*\*\s*\|\s*([^|\n]+?)\s*\|.*?\*\*Status\*\*\s*\|\s*([^|\n]+?)\s*\|.*?\*\*Evidence\*\*\s*\|\s*([^|\n]+?)\s*\|",
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
        if not self.exists():
            return False
        text = self.read()
        task_match = re.search(
            r"\*\*ID\*\*\s*\|\s*(.+?)\n.*?\*\*Name\*\*\s*\|\s*(.+?)\n.*?\*\*Status\*\*\s*\|\s*(.+?)\n.*?\*\*Evidence\*\*\s*\|\s*(.+?)\n",
            text,
            re.DOTALL,
        )
        if not task_match:
            return False
        task_name = task_match.group(2).strip().rstrip("|").strip()
        phase_match = re.search(r"phase:\s*(\d+)", text)
        phase = phase_match.group(1) if phase_match else "0"
        archive_path = create_archive_file(
            self.root,
            task_id,
            task_name,
            evidence,
            phase,
            score=_latest_drift_score(text),
        )
        archive_rel = ""
        if archive_path:
            try:
                # Correct for both layouts: conductor in docs/ or at repo root
                archive_rel = str(archive_path.relative_to(self.path.parent))
            except ValueError:
                archive_rel = str(archive_path)
        old_pattern = re.compile(
            r"(\*\*Status\*\*\s*\|\s*)(.+?)(\n.*?\*\*Evidence\*\*\s*\|\s*)(.*?)(\n)",
            re.DOTALL,
        )

        def replacer(m: re.Match[str]) -> str:
            return f"{m.group(1)}✅ COMPLETE{m.group(3)}{evidence}{m.group(5)}"

        new_text, count = old_pattern.subn(replacer, text, count=1)
        if count == 0:
            return False
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        archive_link = f"[archive]({archive_rel})" if archive_rel else evidence
        archive_row = f"| {task_id} | {task_name} | {now} | {archive_link} | — |"
        lines = new_text.split("\n")
        if _insert_table_row(lines, "## Completed Tasks", "| ID |", archive_row):
            new_text = "\n".join(lines)
        new_text = self._update_timestamp(new_text)
        self.path.write_text(new_text, encoding="utf-8")
        return True

    def block_task(self, task_id: str, reason: str) -> bool:
        if not self.exists():
            return False
        text = self.read()
        lines = text.split("\n")
        new_row = f"| {task_id} | {reason} | discovered during current task | — |"
        if not _insert_table_row(lines, "## Blocked Tasks", "| ID |", new_row):
            return False
        new_text = "\n".join(lines)
        new_text = self._update_timestamp(new_text)
        self.path.write_text(new_text, encoding="utf-8")
        return True

    def next_task(self) -> dict[str, Any]:
        text = self.read()
        if not text:
            return {"error": "Conductor file not found"}
        return {
            "message": "Check the conductor manually for the next ready task.",
            "hint": "Look for tasks in 'Future Tasks' or review 'Blocked Tasks'.",
        }

    def _update_timestamp(self, text: str) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        updated_pattern = re.compile(r"(updated:\s*').*?(')")
        return updated_pattern.sub(rf"\g<1>{now}\g<2>", text, count=1)

    def init(self, force: bool = False) -> Path:
        if self.exists() and not force:
            return self.path
        content = template_text("project-conductor.md.tmpl")
        if content is None:
            content = default_conductor_content()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(content, encoding="utf-8")
        return self.path

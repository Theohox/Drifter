"""Conductor manager — CLI utilities for managing project conductor state."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from drifter.config import Config
from drifter._conductor_helpers import create_archive_file, default_conductor_content


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
                if (
                    line.strip().startswith("|")
                    and "Timestamp" not in line
                    and "---" not in line
                ):
                    if "—" not in line:
                        last_data_idx = i
        if header_idx < 0:
            return
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
            return
        lines.insert(insert_idx + 1, new_row)
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
        task_name = task_match.group(2).strip()
        phase_match = re.search(r"phase:\s*(\d+)", text)
        phase = phase_match.group(1) if phase_match else "0"
        archive_path = create_archive_file(
            self.root, task_id, task_name, evidence, phase
        )
        archive_rel = f"archive/{archive_path.name}" if archive_path else ""
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
                if (
                    line.strip().startswith("|")
                    and "| ID |" not in line
                    and "---" not in line
                ):
                    if "—" not in line:
                        last_data_idx = i
        if header_idx >= 0:
            sep_idx = -1
            for i in range(
                header_idx,
                min(
                    last_data_idx + 2 if last_data_idx >= 0 else len(lines), len(lines)
                ),
            ):
                if "|---" in lines[i] or "| -" in lines[i]:
                    sep_idx = i
                    break
            insert_idx = last_data_idx if last_data_idx >= 0 else sep_idx
            if insert_idx >= 0:
                lines.insert(insert_idx + 1, archive_row)
                new_text = "\n".join(lines)
        new_text = self._update_timestamp(new_text)
        self.path.write_text(new_text, encoding="utf-8")
        return True

    def block_task(self, task_id: str, reason: str) -> bool:
        if not self.exists():
            return False
        text = self.read()
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
                if (
                    line.strip().startswith("|")
                    and "| ID |" not in line
                    and "---" not in line
                ):
                    if "—" not in line:
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
        new_row = f"| {task_id} | {reason} | discovered during current task | — |"
        lines.insert(insert_idx + 1, new_row)
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
        template_path = (
            Path(__file__).parent.parent.parent
            / "templates"
            / "project-conductor.md.tmpl"
        )
        if not template_path.exists():
            template_path = (
                Path(__file__).parent.parent / "templates" / "project-conductor.md.tmpl"
            )
        if template_path.exists():
            content = template_path.read_text(encoding="utf-8")
        else:
            content = default_conductor_content()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(content, encoding="utf-8")
        return self.path

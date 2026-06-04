from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from drifter.checks._base import Check, Issue
from drifter.config import Config

class ConductorHealthCheck:
    """Verify the Conductor file has exactly one active task and valid phase."""

    name = "conductor_health"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        conductor = root / "docs" / "project-conductor.md"
        if not conductor.exists():
            # Also check root-level legacy location
            conductor = root / "project-conductor.md"
        if not conductor.exists():
            issues.append(Issue(
                check=self.name,
                file="project-conductor.md",
                detail="Conductor file does not exist",
                severity="error",
            ))
            return issues

        text = conductor.read_text(encoding="utf-8")

        # Count active tasks
        active_count = text.count("**Active Task**") + text.count("## Active Task")
        if active_count == 0:
            issues.append(Issue(
                check=self.name,
                file=str(conductor.relative_to(root)),
                detail="No active task section found",
                severity="error",
            ))
        elif active_count > 1:
            issues.append(Issue(
                check=self.name,
                file=str(conductor.relative_to(root)),
                detail=f"Found {active_count} active task sections (expected exactly 1)",
                severity="error",
            ))

        # Check current phase is marked active
        if "🟢 ACTIVE" not in text and "🟡 ACTIVE" not in text and "ACTIVE" not in text:
            issues.append(Issue(
                check=self.name,
                file=str(conductor.relative_to(root)),
                detail="No phase marked as ACTIVE",
                severity="warn",
            ))

        return issues

class PipelineIntegrityCheck:
    """Verify conductor task references are consistent and tasks don't exist in multiple states."""

    name = "pipeline_integrity"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        conductor = root / "docs" / "project-conductor.md"
        if not conductor.exists():
            conductor = root / "project-conductor.md"
        if not conductor.exists():
            return issues

        text = conductor.read_text(encoding="utf-8")

        # Collect all task IDs from all sections
        active_ids: set[str] = set()
        blocked_ids: set[str] = set()
        future_ids: set[str] = set()
        completed_ids: set[str] = set()
        all_ids: set[str] = set()

        # Extract IDs from Active Task
        active_match = re.search(r"\*\*ID\*\*\s*\|\s*([^|\n]+?)\s*\|", text)
        if active_match:
            active_id = active_match.group(1).strip()
            if active_id != "—":
                active_ids.add(active_id)
                all_ids.add(active_id)

        # Extract IDs from Blocked Tasks table
        blocked_section = re.search(r"## Blocked Tasks.*?(?=## |\Z)", text, re.DOTALL)
        if blocked_section:
            for line in blocked_section.group(0).split("\n"):
                if line.strip().startswith("|") and "| ID |" not in line and "---" not in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 2 and parts[1] and parts[1] != "—":
                        blocked_ids.add(parts[1])
                        all_ids.add(parts[1])

        # Extract IDs from Future Tasks table
        future_section = re.search(r"## Future Tasks.*?(?=## |\Z)", text, re.DOTALL)
        if future_section:
            for line in future_section.group(0).split("\n"):
                if line.strip().startswith("|") and "| ID |" not in line and "---" not in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 2 and parts[1] and parts[1] != "—":
                        future_ids.add(parts[1])
                        all_ids.add(parts[1])

        # Extract IDs from Completed Tasks table
        completed_section = re.search(r"## Completed Tasks.*?(?=## |\Z)", text, re.DOTALL)
        if completed_section:
            for line in completed_section.group(0).split("\n"):
                if line.strip().startswith("|") and "| ID |" not in line and "---" not in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 2 and parts[1] and parts[1] != "—":
                        completed_ids.add(parts[1])
                        all_ids.add(parts[1])

        # Check for tasks in multiple states
        active_blocked = active_ids & blocked_ids
        if active_blocked:
            issues.append(Issue(
                check=self.name,
                file=str(conductor.relative_to(root)),
                detail=f"Task(s) {active_blocked} appear in both Active and Blocked",
                severity="error",
            ))

        active_future = active_ids & future_ids
        if active_future:
            issues.append(Issue(
                check=self.name,
                file=str(conductor.relative_to(root)),
                detail=f"Task(s) {active_future} appear in both Active and Future",
                severity="warn",
            ))

        # Collect all "Depends On" references from all tables
        depends_on_refs: list[str] = []
        depends_on_pattern = re.compile(r"\*\*Depends On\*\*\s*\|\s*([^|\n]+?)\s*\|")
        for match in depends_on_pattern.finditer(text):
            val = match.group(1).strip().rstrip("|")
            if val and val != "—":
                for ref in val.split(","):
                    ref = ref.strip().rstrip("|")
                    if ref:
                        depends_on_refs.append(ref)

        # Validate Depends On references exist
        for ref_id in depends_on_refs:
            if ref_id not in all_ids:
                issues.append(Issue(
                    check=self.name,
                    file=str(conductor.relative_to(root)),
                    detail=f"Task 'Depends On' references '{ref_id}' which does not exist in any task section",
                    severity="warn",
                ))

        # Detect circular dependencies in Depends On
        adjacency: dict[str, set[str]] = {}
        for match in depends_on_pattern.finditer(text):
            pos = match.start()
            preceding = text[:pos]
            id_match = re.search(r"\*\*ID\*\*\s*\|\s*([^|\n]+?)\s*\|", preceding)
            if id_match:
                owner_id = id_match.group(1).strip()
                deps = {d.strip() for d in match.group(1).strip().split(",") if d.strip() and d.strip() != "—"}
                if owner_id and owner_id != "—":
                    adjacency[owner_id] = deps

        # Also check Blocked Tasks and Future Tasks tables for Depends On
        for section_match in [blocked_section, future_section]:
            if section_match:
                lines = section_match.group(0).split("\n")
                for line in lines:
                    if line.strip().startswith("|") and "| ID |" not in line and "---" not in line:
                        parts = [p.strip() for p in line.split("|")]
                        if len(parts) >= 5 and parts[1] and parts[1] != "—":
                            task_id = parts[1]
                            deps_str = parts[4] if len(parts) > 4 else "—"
                            if deps_str != "—":
                                deps = {d.strip() for d in deps_str.split(",") if d.strip()}
                                adjacency[task_id] = deps

        # Detect cycles using DFS
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adjacency.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in adjacency:
            if node not in visited:
                if has_cycle(node):
                    issues.append(Issue(
                        check=self.name,
                        file=str(conductor.relative_to(root)),
                        detail="Circular dependency detected in task graph: check 'Depends On' references",
                        severity="error",
                    ))
                    break

        # Check that "Next" references exist
        next_match = re.search(r"\*\*Next\*\*\s*\|\s*(.+?)\s*\n", text)
        if next_match:
            next_val = next_match.group(1).strip()
            if next_val != "—" and ":" in next_val:
                ref_id = next_val.split(":")[0].strip()
                if ref_id and ref_id not in all_ids:
                    issues.append(Issue(
                        check=self.name,
                        file=str(conductor.relative_to(root)),
                        detail=f"Active Task 'Next' references '{ref_id}' which does not exist in any task section",
                        severity="warn",
                    ))

        # Check blocked tasks have non-empty Blocked On
        if blocked_section:
            for line in blocked_section.group(0).split("\n"):
                if line.strip().startswith("|") and "| ID |" not in line and "---" not in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 6 and parts[1] and parts[1] != "—":
                        blocked_on = parts[4] if len(parts) > 4 else ""
                        if not blocked_on or blocked_on == "—":
                            issues.append(Issue(
                                check=self.name,
                                file=str(conductor.relative_to(root)),
                                detail=f"Blocked task '{parts[1]}' has empty 'Blocked On' field",
                                severity="warn",
                            ))

        # Check completed tasks have non-empty evidence
        if completed_section:
            for line in completed_section.group(0).split("\n"):
                if line.strip().startswith("|") and "| ID |" not in line and "---" not in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 5 and parts[1] and parts[1] != "—":
                        evidence = parts[4] if len(parts) > 4 else ""
                        if not evidence or evidence == "—":
                            issues.append(Issue(
                                check=self.name,
                                file=str(conductor.relative_to(root)),
                                detail=f"Completed task '{parts[1]}' has empty evidence",
                                severity="warn",
                            ))

        return issues

class ConductorContentCheck:
    """Verify conductor contains current data (non-empty evidence, score history)."""

    name = "conductor_content"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        conductor = root / "docs" / "project-conductor.md"
        if not conductor.exists():
            conductor = root / "project-conductor.md"
        if not conductor.exists():
            return issues

        text = conductor.read_text(encoding="utf-8")

        # Check drift score history is not empty
        history_match = re.search(r"## Drift Score History.*?(?=## |\Z)", text, re.DOTALL)
        if history_match:
            history_text = history_match.group(0)
            data_rows = [
                line for line in history_text.split("\n")
                if line.strip().startswith("|")
                and "—" not in line
                and "Timestamp" not in line
                and "---" not in line
            ]
            if not data_rows:
                issues.append(Issue(
                    check=self.name,
                    file=str(conductor.relative_to(root)),
                    detail="Drift Score History is empty — run 'drifter check' to populate",
                    severity="warn",
                ))

        # Check active task evidence isn't just a placeholder
        for line in text.split("\n"):
            if "**Evidence**" in line and "|" in line:
                parts = [p.strip() for p in line.split("|")]
                evidence_vals = [p for p in parts if p and p != "**Evidence**"]
                if evidence_vals:
                    evidence = evidence_vals[0]
                    if evidence in ("—", "-", ""):
                        issues.append(Issue(
                            check=self.name,
                            file=str(conductor.relative_to(root)),
                            detail="Active Task evidence is empty",
                            severity="warn",
                        ))
                break

        return issues

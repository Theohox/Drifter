"""Document validation internals — extracted from doc_validator.py."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dataclasses import dataclass

VALID_TYPES = {
    "constitution",
    "snapshot",
    "backlog",
    "archive",
    "playbook",
    "guide",
    "reference",
    "index",
}

VALID_STATUSES = {
    "active",
    "draft",
    "archived",
    "deprecated",
}


@dataclass(frozen=True)
class DocIssue:
    file: str
    detail: str
    severity: str = "warn"

    def __repr__(self) -> str:
        return f"[{self.severity.upper()}] {self.file} — {self.detail}"


def _parse_frontmatter(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip("'\"")
            result[key] = value
    return result


def _validate_single(md_file: Path, root: Path) -> list[DocIssue]:
    issues: list[DocIssue] = []
    rel_path = str(md_file.relative_to(root))
    text = md_file.read_text(encoding="utf-8")

    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not frontmatter_match:
        issues.append(DocIssue(file=rel_path, detail="Missing YAML frontmatter", severity="error"))
        return issues

    frontmatter = _parse_frontmatter(frontmatter_match.group(1))

    if "type" not in frontmatter:
        issues.append(DocIssue(file=rel_path, detail="Missing 'type:' in frontmatter", severity="error"))
    else:
        doc_type = frontmatter["type"]
        if doc_type not in VALID_TYPES:
            issues.append(DocIssue(
                file=rel_path,
                detail=f"Invalid type '{doc_type}'. Valid: {', '.join(sorted(VALID_TYPES))}",
                severity="error",
            ))

    if "status" not in frontmatter:
        issues.append(DocIssue(file=rel_path, detail="Missing 'status:' in frontmatter", severity="warn"))
    else:
        doc_status = frontmatter["status"]
        if doc_status not in VALID_STATUSES:
            issues.append(DocIssue(
                file=rel_path,
                detail=f"Invalid status '{doc_status}'. Valid: {', '.join(sorted(VALID_STATUSES))}",
                severity="warn",
            ))

    if "phase" in frontmatter:
        try:
            int(frontmatter["phase"])
        except ValueError:
            issues.append(DocIssue(
                file=rel_path,
                detail=f"Invalid phase '{frontmatter['phase']}'. Must be an integer.",
                severity="warn",
            ))

    for field in ("title", "created"):
        if field not in frontmatter:
            issues.append(DocIssue(file=rel_path, detail=f"Missing '{field}:' in frontmatter", severity="warn"))

    if "version" in frontmatter:
        version = frontmatter["version"]
        if not re.match(r'^\d+\.\d+(\.\d+)?$', version):
            issues.append(DocIssue(
                file=rel_path,
                detail=f"Invalid version '{version}'. Must be semver (e.g. 1.0 or 1.0.0).",
                severity="warn",
            ))

    if "updated" not in frontmatter:
        issues.append(DocIssue(file=rel_path, detail="Missing 'updated:' timestamp in frontmatter", severity="warn"))
    else:
        created = frontmatter.get("created", "")
        updated = frontmatter.get("updated", "")
        if created and updated:
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                if updated_dt < created_dt:
                    issues.append(DocIssue(
                        file=rel_path,
                        detail="'updated' timestamp is older than 'created'",
                        severity="error",
                    ))
            except ValueError:
                pass

    doc_type = frontmatter.get("type", "")
    if doc_type == "snapshot":
        body = text[frontmatter_match.end():]
        if len(body) > 10000:
            issues.append(DocIssue(
                file=rel_path,
                detail="Snapshot document is very long (>10k chars). Consider rewriting or splitting.",
                severity="warn",
            ))

    return issues

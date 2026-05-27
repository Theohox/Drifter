"""Document validator — validates document type rules and frontmatter."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from drifter.config import Config

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


@dataclass(frozen=True)
class DocIssue:
    file: str
    detail: str
    severity: str = "warn"  # "error" | "warn" | "info"

    def __repr__(self) -> str:
        return f"[{self.severity.upper()}] {self.file} — {self.detail}"


@dataclass
class DocReport:
    total: int
    errors: int
    warns: int
    issues: list[DocIssue] = field(default_factory=list)


def validate_docs(root: Path | None = None, config: Config | None = None) -> DocReport:
    """Validate all markdown documents in the project."""
    if config is None:
        config = Config.load(root)
    if root is None:
        root = config.root

    issues: list[DocIssue] = []

    # Find all markdown files
    md_files: list[Path] = []
    docs_dir = root / "docs"
    if docs_dir.exists():
        md_files.extend(docs_dir.rglob("*.md"))
    md_files.extend(root.glob("*.md"))

    for md_file in md_files:
        if config.is_ignored(md_file):
            continue
        # Skip root-level files that are not in docs/ — these don't need frontmatter
        if md_file.parent == root and md_file.name in ("README.md", "AGENTS.md", "LICENSE", "CONTRIBUTING.md"):
            continue
        issues.extend(_validate_single(md_file, root))

    errors = sum(1 for i in issues if i.severity == "error")
    warns = sum(1 for i in issues if i.severity == "warn")

    return DocReport(
        total=len(issues),
        errors=errors,
        warns=warns,
        issues=issues,
    )


def _validate_single(md_file: Path, root: Path) -> list[DocIssue]:
    issues: list[DocIssue] = []
    rel_path = str(md_file.relative_to(root))
    text = md_file.read_text(encoding="utf-8")

    # Parse frontmatter
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not frontmatter_match:
        issues.append(DocIssue(
            file=rel_path,
            detail="Missing YAML frontmatter",
            severity="error",
        ))
        return issues

    frontmatter_text = frontmatter_match.group(1)
    frontmatter = _parse_frontmatter(frontmatter_text)

    # Check required fields
    if "type" not in frontmatter:
        issues.append(DocIssue(
            file=rel_path,
            detail="Missing 'type:' in frontmatter",
            severity="error",
        ))
    else:
        doc_type = frontmatter["type"]
        if doc_type not in VALID_TYPES:
            issues.append(DocIssue(
                file=rel_path,
                detail=f"Invalid type '{doc_type}'. Valid: {', '.join(sorted(VALID_TYPES))}",
                severity="error",
            ))

    if "title" not in frontmatter:
        issues.append(DocIssue(
            file=rel_path,
            detail="Missing 'title:' in frontmatter",
            severity="warn",
        ))

    if "created" not in frontmatter:
        issues.append(DocIssue(
            file=rel_path,
            detail="Missing 'created:' timestamp in frontmatter",
            severity="warn",
        ))

    if "updated" not in frontmatter:
        issues.append(DocIssue(
            file=rel_path,
            detail="Missing 'updated:' timestamp in frontmatter",
            severity="warn",
        ))
    else:
        # Validate updated >= created
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

    # Type-specific validations
    doc_type = frontmatter.get("type", "")
    if doc_type == "snapshot":
        # Check for append-only growth (heuristic: document is very long)
        body = text[frontmatter_match.end():]
        if len(body) > 10000:
            issues.append(DocIssue(
                file=rel_path,
                detail="Snapshot document is very long (>10k chars). Consider rewriting or splitting.",
                severity="warn",
            ))

    return issues


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Simple YAML frontmatter parser (handles only key: value pairs)."""
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

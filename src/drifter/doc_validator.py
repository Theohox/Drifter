"""Document validator — validates document type rules and frontmatter."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from drifter.config import Config
from drifter._doc_validate import _validate_single, DocIssue


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
    md_files: list[Path] = []
    docs_dir = root / "docs"
    if docs_dir.exists():
        md_files.extend(docs_dir.rglob("*.md"))
    md_files.extend(root.glob("*.md"))

    for md_file in md_files:
        if config.is_ignored(md_file):
            continue
        if md_file.parent == root and md_file.name in ("README.md", "AGENTS.md", "LICENSE", "CONTRIBUTING.md"):
            continue
        issues.extend(_validate_single(md_file, root))

    errors = sum(1 for i in issues if i.severity == "error")
    warns = sum(1 for i in issues if i.severity == "warn")
    return DocReport(total=len(issues), errors=errors, warns=warns, issues=issues)

"""Shared helpers for drift checks."""

from __future__ import annotations

from pathlib import Path

from drifter._toml_utils import safe_load_toml
from drifter.checks._base import Issue

# Substrings that mark a referenced path as a placeholder/example, not a
# real file that must exist. Shared by StaleReferenceCheck and
# HardcodedPathCheck so the two sets cannot drift apart.
PATH_SKIP_PATTERNS = {
    "http",
    "https",
    "mailto",
    "#",
    "..",
    "./",
    "example",
    "your_",
    "my_",
    "agent_name",
    "skill_name",
    "yyyy-mm-dd",
    "YYYY-MM-DD",
    ".kimi/",
    ".claude/",
    ".drifter/",
    ".cursor/",
    "nonexistent",
    "not_found",
    "not found",
    "missing_",
    # Common documentation examples that may not exist in all projects
    "purpose.md",
    "current_state.md",
    "agent_open.md",
    "agent_closed.md",
    "ops-playbook.md",
    "contributing.md",
    "api-reference.md",
    "session-*.md",  # wildcard patterns in examples
}


def is_skippable_path(path_str: str) -> bool:
    """True if a referenced path looks like a placeholder or example."""
    lower = path_str.lower()
    return any(skip in lower for skip in PATH_SKIP_PATTERNS)


def resolve_doc_path(root: Path, path_str: str) -> Path:
    """Resolve a referenced path against the root, falling back to docs/."""
    candidate = root / path_str
    if not candidate.exists():
        docs_dir = root / "docs"
        if docs_dir.exists():
            candidate = docs_dir / path_str
    return candidate


def load_drifter_manifest(
    root: Path, check_name: str
) -> tuple[dict | None, Issue | None]:
    """Load drifter-manifest.toml.

    Returns (manifest, None) on success, (None, None) when the manifest
    does not exist, and (None, Issue) when it exists but cannot be parsed.
    """
    manifest_file = root / "drifter-manifest.toml"
    if not manifest_file.exists():
        return None, None
    manifest = safe_load_toml(manifest_file)
    if manifest is None:
        return None, Issue(
            check=check_name,
            file="drifter-manifest.toml",
            detail="Cannot parse drifter-manifest.toml — file may be corrupted",
            severity="error",
        )
    return manifest, None


def archive_designated_docs(manifest: dict) -> set[str]:
    """Return docs-relative paths designated type = "archive" in [tree.docs]."""
    docs_tree = manifest.get("tree", {}).get("docs", {})
    archived: set[str] = set()

    def _collect(node: dict, prefix: str) -> None:
        for key, val in node.items():
            if not isinstance(val, dict):
                continue
            if val.get("type") == "archive":
                archived.add(prefix + key)
            else:
                _collect(val, f"{prefix}{key}/")

    _collect(docs_tree, "")
    return archived

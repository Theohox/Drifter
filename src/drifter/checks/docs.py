from __future__ import annotations
from datetime import datetime, timedelta, timezone

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

class StaleReferenceCheck:
    """Scan markdown files for file/path references and verify they exist."""

    name = "stale_reference"

    _PATH_PATTERNS = [
        re.compile(r"`([^`]+\.(?:py|rs|md|toml|json|yaml|txt|cfg|sh|js|ts|go|java|cpp|c|h))`"),
        re.compile(r"\[([^\]]+)\]\(([^)]+)\)"),
        re.compile(r"(?:^|\s)([\w/\-\.]+\.(?:py|rs|md|toml|json|yaml|txt|js|ts|go|java|cpp|c|h))"),
    ]

    _SKIP_PATTERNS = {
        "http", "https", "mailto", "#", "..", "./",
        "example", "your_", "my_", "agent_name", "skill_name",
        "yyyy-mm-dd", "YYYY-MM-DD",
        ".kimi/", ".claude/", ".cursor/",
        # Common documentation examples that may not exist in all projects
        "purpose.md", "current_state.md", "agent_open.md", "agent_closed.md",
        "ops-playbook.md", "contributing.md", "api-reference.md",
        "session-*.md",  # wildcard patterns in examples
    }

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        wiki_dir = root / "docs"
        md_files = list(wiki_dir.rglob("*.md")) if wiki_dir.exists() else []
        md_files.extend(root.glob("*.md"))

        for md_file in md_files:
            if config.is_ignored(md_file):
                continue
            # Skip archive files — they are historical records and may reference
            # files that no longer exist (merged, renamed, or deleted)
            if "docs/archive" in str(md_file):
                continue
            text = md_file.read_text(encoding="utf-8")
            for pattern in self._PATH_PATTERNS:
                for match in pattern.finditer(text):
                    path_str = match.group(2) if len(match.groups()) >= 2 and match.group(2) else match.group(1)
                    if self._should_skip(path_str):
                        continue
                    candidate = root / path_str
                    if not candidate.exists():
                        candidate = wiki_dir / path_str if wiki_dir.exists() else candidate
                    if not candidate.exists() and "/" in path_str and len(path_str) > 5:
                        issues.append(Issue(
                            check=self.name,
                            file=str(md_file.relative_to(root)),
                            detail=f"references '{path_str}' which does not exist",
                            severity="warn",
                        ))
        return issues

    def _should_skip(self, path_str: str) -> bool:
        lower = path_str.lower()
        if any(lower.startswith(p) for p in self._SKIP_PATTERNS):
            return True
        for skip in self._SKIP_PATTERNS:
            if skip in lower:
                return True
        return False

class CrossDocConsistencyCheck:
    """Check for cross-document inconsistencies (e.g., stale references between docs)."""

    name = "cross_doc_consistency"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        docs_dir = root / "docs"
        if not docs_dir.exists():
            return issues

        # Gather all internal doc links
        doc_links: dict[str, list[str]] = {}  # target -> [source files]
        md_files = list(docs_dir.rglob("*.md"))
        md_files.extend(root.glob("*.md"))

        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")

        for md_file in md_files:
            if config.is_ignored(md_file):
                continue
            text = md_file.read_text(encoding="utf-8")
            for match in link_pattern.finditer(text):
                target = match.group(2)
                if target.startswith("http"):
                    continue
                # Resolve relative to current doc
                source_dir = md_file.parent
                target_path = (source_dir / target).resolve()
                if not target_path.exists():
                    rel_target = str(target_path.relative_to(root)) if target_path.is_relative_to(root) else target
                    issues.append(Issue(
                        check=self.name,
                        file=str(md_file.relative_to(root)),
                        detail=f"links to '{target}' which does not exist",
                        severity="warn",
                    ))

        return issues

class TimestampStalenessCheck:
    """Check that markdown frontmatter 'updated:' timestamps reflect actual file modification time."""

    name = "timestamp_staleness"
    _TIMESTAMP_PATTERN = re.compile(r"updated:\s*['\"]?(.*?)['\"]?$", re.MULTILINE)

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        md_files: list[Path] = []
        docs_dir = root / "docs"
        if docs_dir.exists():
            md_files.extend(docs_dir.rglob("*.md"))
        md_files.extend(root.glob("*.md"))

        for md_file in md_files:
            if config.is_ignored(md_file):
                continue
            text = md_file.read_text(encoding="utf-8")
            match = self._TIMESTAMP_PATTERN.search(text)
            if not match:
                continue
            try:
                date_str = match.group(1).strip().strip("'\"")
                updated_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                mtime = datetime.fromtimestamp(md_file.stat().st_mtime, tz=timezone.utc)
                if mtime - updated_dt > timedelta(hours=1):
                    hours = int((mtime - updated_dt).total_seconds() / 3600)
                    issues.append(Issue(
                        check=self.name,
                        file=str(md_file.relative_to(root)),
                        detail=f"updated timestamp is {hours}h older than file mtime",
                        severity="warn",
                    ))
            except Exception:
                pass
        return issues

class DigestStalenessCheck:
    """Check digests for PENDING/TODO items older than threshold."""

    name = "digest_staleness"

    _STALE_KEYWORDS = re.compile(r"\b(PENDING|TODO|BLOCKED|WAITING)\b", re.IGNORECASE)

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        digests_dir = root / "docs" / "digests"
        if not digests_dir.exists():
            return issues

        for digest_file in digests_dir.rglob("*.md"):
            if config.is_ignored(digest_file):
                continue
            text = digest_file.read_text(encoding="utf-8")
            age_days = self._get_age_days(text)
            stale_matches = self._STALE_KEYWORDS.findall(text)
            if stale_matches and age_days > config.max_pending_age_days:
                issues.append(Issue(
                    check=self.name,
                    file=str(digest_file.relative_to(root)),
                    detail=f"has {len(stale_matches)} pending items, last updated {age_days} days ago",
                    severity="warn",
                ))
        return issues

    def _get_age_days(self, text: str) -> int:
        for line in text.split("\n"):
            if line.strip().startswith("updated:"):
                date_str = line.split(":", 1)[1].strip().strip("'\" ")
                try:
                    updated_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    return (datetime.now(timezone.utc) - updated_dt).days
                except Exception:
                    pass
                break
        return 0

class ArchiveIntegrityCheck:
    """Verify archive files have valid frontmatter and consistent naming."""

    name = "archive_integrity"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        archive_dir = root / "docs" / "archive"
        if not archive_dir.exists():
            return issues

        for archive_file in archive_dir.glob("*.md"):
            if archive_file.name == "README.md":
                continue
            if config.is_ignored(archive_file):
                continue

            text = archive_file.read_text(encoding="utf-8")
            rel_path = str(archive_file.relative_to(root))

            # Parse frontmatter
            frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
            if not frontmatter_match:
                issues.append(Issue(
                    check=self.name,
                    file=rel_path,
                    detail="Missing YAML frontmatter",
                    severity="error",
                ))
                continue

            frontmatter_text = frontmatter_match.group(1)
            frontmatter: dict[str, str] = {}
            for line in frontmatter_text.split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, value = line.split(":", 1)
                    frontmatter[key.strip()] = value.strip().strip("'\"")

            # Check type is archive
            doc_type = frontmatter.get("type", "")
            if doc_type != "archive":
                issues.append(Issue(
                    check=self.name,
                    file=rel_path,
                    detail=f"Invalid type '{doc_type}' (expected 'archive')",
                    severity="error",
                ))

            # Check task_id exists
            task_id = frontmatter.get("task_id", "")
            if not task_id:
                issues.append(Issue(
                    check=self.name,
                    file=rel_path,
                    detail="Missing 'task_id' in frontmatter",
                    severity="error",
                ))
                continue

            # Check filename matches task_id
            expected_prefix = f"{task_id}-"
            if not archive_file.name.startswith(expected_prefix):
                issues.append(Issue(
                    check=self.name,
                    file=rel_path,
                    detail=f"Filename '{archive_file.name}' does not match task_id '{task_id}' (expected prefix '{expected_prefix}')",
                    severity="error",
                ))

        return issues

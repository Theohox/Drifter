"""Drift Guard — Universal drift detection engine.

Scans a project for drift between code, docs, and project state.
Plugin-based: each check is a self-contained callable.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from drifter.config import Config


# ── Issue Dataclass ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Issue:
    check: str
    file: str
    detail: str
    severity: str = "warn"  # "error" | "warn" | "info"

    def __repr__(self) -> str:
        return f"[{self.severity.upper()}] {self.check}: {self.file} — {self.detail}"


# ── Check Protocol ──────────────────────────────────────────────────────────

class Check(Protocol):
    name: str

    def run(self, root: Path, config: Config) -> list[Issue]: ...


# ── Built-in Checks ─────────────────────────────────────────────────────────

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


class HardcodedPathCheck:
    """Scan source files for hardcoded paths and verify they exist."""

    name = "hardcoded_path"

    _PATH_PATTERN = re.compile(
        r'["\']((?:docs|src|tests|config|tools|scripts|wiki|core|guides|reference)/[\w/\-\.]+)["\']'
    )

    _SKIP_PATTERNS = {
        "example", "agent_name", "skill_name", "your_", "my_",
        "yyyy-mm-dd", "YYYY-MM-DD", "nonexistent", "not_found",
        "not found", "missing_",
    }

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        source_exts = (".py", ".rs", ".js", ".ts", ".go", ".java", ".sh", ".toml", ".yaml", ".yml")

        for ext in source_exts:
            for src_file in root.rglob(f"*{ext}"):
                if config.is_ignored(src_file):
                    continue
                # Skip this file itself, __pycache__, and test files
                str_path = str(src_file)
                if "__pycache__" in str_path or src_file.name == "drift_guard.py":
                    continue
                if "/tests/" in str_path or str_path.startswith("tests/"):
                    continue
                text = src_file.read_text(encoding="utf-8")
                for match in self._PATH_PATTERN.finditer(text):
                    path_str = match.group(1)
                    if self._should_skip(path_str):
                        continue
                    candidate = root / path_str
                    if not candidate.exists():
                        candidate = root / "docs" / path_str if (root / "docs").exists() else candidate
                    if not candidate.exists():
                        issues.append(Issue(
                            check=self.name,
                            file=str(src_file.relative_to(root)),
                            detail=f"hardcodes '{path_str}' which does not exist",
                            severity="error",
                        ))
        return issues

    def _should_skip(self, path_str: str) -> bool:
        lower = path_str.lower()
        for skip in self._SKIP_PATTERNS:
            if skip in lower:
                return True
        return False


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


class GitSafetyCheck:
    """Scan source files for git mutation commands in shell calls or subprocess."""

    name = "git_safety"

    # Patterns that look like git history mutation in code
    _GIT_PATTERNS = [
        re.compile(r'git\s+(commit|push|reset|rebase|merge|cherry-pick|tag)\s'),
        re.compile(r'git\s+checkout\s+-b'),
        re.compile(r'subprocess\.\w+.*git\s+(commit|push|reset|rebase|merge)'),
        re.compile(r'os\.system\(.*git\s+(commit|push|reset|rebase|merge)'),
        re.compile(r'["\']git\s+(commit|push|reset|rebase|merge|cherry-pick|tag)["\']'),
    ]

    # Safe informational commands we don't flag
    _SAFE_COMMANDS = {"git status", "git diff", "git log", "git show", "git branch"}

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        source_exts = (".py", ".rs", ".js", ".ts", ".go", ".java", ".sh", ".rb")

        for ext in source_exts:
            for src_file in root.rglob(f"*{ext}"):
                if config.is_ignored(src_file):
                    continue
                str_path = str(src_file)
                if "/tests/" in str_path or str_path.startswith("tests/"):
                    continue
                text = src_file.read_text(encoding="utf-8")
                for pattern in self._GIT_PATTERNS:
                    for match in pattern.finditer(text):
                        matched_text = match.group(0)
                        # Skip if it's just documenting the rule itself
                        if any(safe in matched_text.lower() for safe in self._SAFE_COMMANDS):
                            continue
                        # Skip comments that mention git commands for documentation
                        line_start = text.rfind("\n", 0, match.start()) + 1
                        line = text[line_start:match.start()]
                        if line.strip().startswith("#") or line.strip().startswith("//"):
                            continue
                        issues.append(Issue(
                            check=self.name,
                            file=str(src_file.relative_to(root)),
                            detail=f"potential git mutation command: '{matched_text.strip()}'",
                            severity="error",
                        ))
        return issues


class DangerousPatternsCheck:
    """Verify dangerous_patterns.toml exists and is referenced in AGENTS.md."""

    name = "dangerous_patterns"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        patterns_file = root / "dangerous_patterns.toml"
        agents_md = root / "AGENTS.md"

        # Check file exists
        if not patterns_file.exists():
            issues.append(Issue(
                check=self.name,
                file="dangerous_patterns.toml",
                detail="dangerous_patterns.toml does not exist at repo root — agents have no command boundaries",
                severity="error",
            ))
            return issues

        # Check it's valid TOML
        try:
            import tomllib
            with patterns_file.open("rb") as f:
                data = tomllib.load(f)
            # Check required sections exist
            if "git" not in data:
                issues.append(Issue(
                    check=self.name,
                    file="dangerous_patterns.toml",
                    detail="Missing [git] section",
                    severity="warn",
                ))
            if "shell" not in data:
                issues.append(Issue(
                    check=self.name,
                    file="dangerous_patterns.toml",
                    detail="Missing [shell] section",
                    severity="warn",
                ))
        except Exception as e:
            issues.append(Issue(
                check=self.name,
                file="dangerous_patterns.toml",
                detail=f"Invalid TOML: {e}",
                severity="error",
            ))

        # Check AGENTS.md references it
        if agents_md.exists():
            agents_text = agents_md.read_text(encoding="utf-8")
            if "dangerous_patterns.toml" not in agents_text:
                issues.append(Issue(
                    check=self.name,
                    file="AGENTS.md",
                    detail="AGENTS.md does not reference dangerous_patterns.toml — agents may not know to read it",
                    severity="error",
                ))
        else:
            issues.append(Issue(
                check=self.name,
                file="AGENTS.md",
                detail="AGENTS.md does not exist",
                severity="error",
            ))

        return issues


# ── Check Registry ──────────────────────────────────────────────────────────

BUILTIN_CHECKS: dict[str, type[Check]] = {
    "stale_reference": StaleReferenceCheck,
    "hardcoded_path": HardcodedPathCheck,
    "digest_staleness": DigestStalenessCheck,
    "conductor_health": ConductorHealthCheck,
    "cross_doc_consistency": CrossDocConsistencyCheck,
    "git_safety": GitSafetyCheck,
    "dangerous_patterns": DangerousPatternsCheck,
}


# ── Report Generation ───────────────────────────────────────────────────────

@dataclass
class Report:
    score: int
    total: int
    errors: int
    warns: int
    infos: int
    issues: list[Issue] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __repr__(self) -> str:
        return (
            f"Report(score={self.score}, total={self.total}, "
            f"errors={self.errors}, warns={self.warns})"
        )


def run_checks(root: Path | None = None, config: Config | None = None) -> Report:
    """Run all enabled checks and return a report."""
    if config is None:
        config = Config.load(root)
    if root is None:
        root = config.root

    all_issues: list[Issue] = []

    # Build check instances
    checks_to_run: list[Check] = []
    for check_cfg in config.checks:
        if not check_cfg.enabled:
            continue
        if check_cfg.name in BUILTIN_CHECKS:
            checks_to_run.append(BUILTIN_CHECKS[check_cfg.name]())
        # TODO: load custom checks from check_cfg.path

    # Run checks (parallel if enough checks)
    if len(checks_to_run) > 1:
        with ThreadPoolExecutor(max_workers=min(len(checks_to_run), 4)) as executor:
            futures = [executor.submit(check.run, root, config) for check in checks_to_run]
            for future in futures:
                try:
                    all_issues.extend(future.result())
                except Exception as e:
                    all_issues.append(Issue(
                        check="engine",
                        file="drift_guard.py",
                        detail=f"Check failed with exception: {e}",
                        severity="error",
                    ))
    else:
        for check in checks_to_run:
            try:
                all_issues.extend(check.run(root, config))
            except Exception as e:
                all_issues.append(Issue(
                    check="engine",
                    file="drift_guard.py",
                    detail=f"Check failed with exception: {e}",
                    severity="error",
                ))

    errors = sum(1 for i in all_issues if i.severity == "error")
    warns = sum(1 for i in all_issues if i.severity == "warn")
    infos = sum(1 for i in all_issues if i.severity == "info")
    total = len(all_issues)

    # Score: 100 - (errors*10 + warns*2), floor at 0
    score = max(0, 100 - errors * 10 - warns * 2)

    return Report(
        score=score,
        total=total,
        errors=errors,
        warns=warns,
        infos=infos,
        issues=all_issues,
    )

"""Drift Guard — Universal drift detection engine.

Scans a project for drift between code, docs, and project state.
Plugin-based: each check is a self-contained callable.
"""

from __future__ import annotations

import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Protocol

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

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


class ArchitectureDocSyncCheck:
    """Verify architecture.md reflects current number of checks and CLI commands."""

    name = "architecture_doc_sync"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        arch_file = root / "docs" / "architecture.md"
        if not arch_file.exists():
            return issues

        arch_text = arch_file.read_text(encoding="utf-8")

        drift_guard = root / "src" / "drifter" / "drift_guard.py"
        if drift_guard.exists():
            guard_text = drift_guard.read_text(encoding="utf-8")
            actual_checks = len(re.findall(r"class \w+Check:", guard_text))
            listed_checks = len(re.findall(r"•\s+\w+Check", arch_text))
            if listed_checks > 0 and actual_checks != listed_checks:
                issues.append(Issue(
                    check=self.name,
                    file="docs/architecture.md",
                    detail=f"lists {listed_checks} checks but drift_guard.py has {actual_checks}",
                    severity="warn",
                ))

        cli_file = root / "src" / "drifter" / "cli.py"
        if cli_file.exists():
            cli_text = cli_file.read_text(encoding="utf-8")
            actual_commands = len(re.findall(r'subparsers\.add_parser\("([^"]+)"', cli_text))
            listed_commands = len(re.findall(r"`drifter \w+`", arch_text))
            if listed_commands > 0 and actual_commands != listed_commands:
                issues.append(Issue(
                    check=self.name,
                    file="docs/architecture.md",
                    detail=f"lists {listed_commands} CLI commands but cli.py has {actual_commands}",
                    severity="warn",
                ))

        # Check templates/drifter.toml.tmpl for hardcoded check counts
        toml_tmpl = root / "templates" / "drifter.toml.tmpl"
        if toml_tmpl.exists() and drift_guard.exists():
            toml_text = toml_tmpl.read_text(encoding="utf-8")
            check_count_match = re.search(r"Built-in checks \((\d+) total\)", toml_text)
            if check_count_match:
                listed = int(check_count_match.group(1))
                if listed != actual_checks:
                    issues.append(Issue(
                        check=self.name,
                        file="templates/drifter.toml.tmpl",
                        detail=f"claims {listed} built-in checks but drift_guard.py has {actual_checks}",
                        severity="warn",
                    ))

        return issues


class ReadmeCompletenessCheck:
    """Verify README.md mentions all canonical artifacts and CLI commands."""

    name = "readme_completeness"

    _REQUIRED_MENTIONS = [
        "AGENTS.md",
        "dangerous_patterns.toml",
        "session-protocol.md",
        "project-conductor.md",
        "drifter check",
        "drifter preflight",
        "drifter conductor",
        "drifter validate",
        "drifter audit",
        "drifter init",
    ]

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        readme = root / "README.md"
        if not readme.exists():
            issues.append(Issue(
                check=self.name,
                file="README.md",
                detail="README.md does not exist",
                severity="warn",
            ))
            return issues

        text = readme.read_text(encoding="utf-8")
        for mention in self._REQUIRED_MENTIONS:
            if mention not in text:
                issues.append(Issue(
                    check=self.name,
                    file="README.md",
                    detail=f"does not mention '{mention}'",
                    severity="warn",
                ))

        return issues


class PreFlightSyncCheck:
    """Verify pre_flight.py and session-protocol.md agree on step count and dangerous_patterns."""

    name = "pre_flight_sync"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        preflight_file = root / "src" / "drifter" / "pre_flight.py"
        protocol_file = root / "docs" / "session-protocol.md"

        if not preflight_file.exists():
            return issues

        preflight_text = preflight_file.read_text(encoding="utf-8")
        preflight_steps = len(re.findall(r"# Step \d+:", preflight_text))

        # Check pre_flight.py docstrings for step count consistency
        for match in re.finditer(r"(\d+)-step pre-flight", preflight_text, re.IGNORECASE):
            listed = int(match.group(1))
            if listed != preflight_steps:
                issues.append(Issue(
                    check=self.name,
                    file="src/drifter/pre_flight.py",
                    detail=f"docstring claims {listed}-step pre-flight but file has {preflight_steps} steps",
                    severity="warn",
                ))
                break

        # Check session-protocol.md
        if protocol_file.exists():
            protocol_text = protocol_file.read_text(encoding="utf-8")
            protocol_steps = 0
            in_preflight = False
            for line in protocol_text.split("\n"):
                if re.search(r"## The \d+-Step Pre-Flight", line):
                    in_preflight = True
                    continue
                if in_preflight and line.strip().startswith("## "):
                    break
                if in_preflight and re.match(r"^\d+\.\s+(READ|RUN|PICK|GREP)", line):
                    protocol_steps += 1

            if preflight_steps != protocol_steps and preflight_steps > 0 and protocol_steps > 0:
                issues.append(Issue(
                    check=self.name,
                    file="docs/session-protocol.md",
                    detail=f"pre_flight.py has {preflight_steps} steps but protocol lists {protocol_steps}",
                    severity="warn",
                ))

            dp_in_protocol = "dangerous_patterns.toml" in protocol_text
            if not dp_in_protocol:
                issues.append(Issue(
                    check=self.name,
                    file="docs/session-protocol.md",
                    detail="does not mention dangerous_patterns.toml in pre-flight steps",
                    severity="warn",
                ))

        # Check methodology.md for step count consistency
        methodology_file = root / "docs" / "methodology.md"
        if methodology_file.exists():
            methodology_text = methodology_file.read_text(encoding="utf-8")
            for match in re.finditer(r"(\d+)-step pre-flight", methodology_text, re.IGNORECASE):
                listed = int(match.group(1))
                if listed != preflight_steps:
                    issues.append(Issue(
                        check=self.name,
                        file="docs/methodology.md",
                        detail=f"claims {listed}-step pre-flight but pre_flight.py has {preflight_steps} steps",
                        severity="warn",
                    ))
                    break

        # Check README.md for step count consistency
        readme_file = root / "README.md"
        if readme_file.exists():
            readme_text = readme_file.read_text(encoding="utf-8")
            for match in re.finditer(r"(\d+)-step pre-flight", readme_text, re.IGNORECASE):
                listed = int(match.group(1))
                if listed != preflight_steps:
                    issues.append(Issue(
                        check=self.name,
                        file="README.md",
                        detail=f"claims {listed}-step pre-flight but pre_flight.py has {preflight_steps} steps",
                        severity="warn",
                    ))
                    break

        dp_in_preflight = "dangerous_patterns.toml" in preflight_text
        if not dp_in_preflight:
            issues.append(Issue(
                check=self.name,
                file="src/drifter/pre_flight.py",
                detail="does not verify dangerous_patterns.toml exists",
                severity="warn",
            ))

        return issues


class CredentialLeakCheck:
    """Scan source files for hardcoded credentials and secrets."""

    name = "credential_leak"

    _PATTERNS: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "OpenAI API key"),
        (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub PAT"),
        (re.compile(r"gho_[a-zA-Z0-9]{36}"), "GitHub OAuth token"),
        (re.compile(r"ghs_[a-zA-Z0-9]{36}"), "GitHub server-to-server token"),
        (re.compile(r"ghu_[a-zA-Z0-9]{36}"), "GitHub user token"),
        (re.compile(r"glpat-[a-zA-Z0-9\-]{20}"), "GitLab PAT"),
        (re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}"), "Bearer token"),
        (re.compile(r"password\s*=\s*['\"][^'\"]{4,}['\"]"), "hardcoded password"),
        (re.compile(r"secret\s*=\s*['\"][^'\"]{4,}['\"]"), "hardcoded secret"),
        (re.compile(r"token\s*=\s*['\"][^'\"]{8,}['\"]"), "hardcoded token"),
    ]

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        source_exts = (".py", ".rs", ".js", ".ts", ".go", ".java", ".sh", ".yaml", ".yml", ".toml")

        for ext in source_exts:
            for src_file in root.rglob(f"*{ext}"):
                if config.is_ignored(src_file):
                    continue
                str_path = str(src_file)
                if "/tests/" in str_path or str_path.startswith("tests/"):
                    continue
                text = src_file.read_text(encoding="utf-8")
                for pattern, label in self._PATTERNS:
                    for match in pattern.finditer(text):
                        line_start = text.rfind("\n", 0, match.start()) + 1
                        line = text[line_start:match.start()]
                        if line.strip().startswith(("#", "//")):
                            continue
                        val = match.group(0)
                        lower = val.lower()
                        if "example" in lower or "your_" in lower or "placeholder" in lower or "xxx" in lower:
                            continue
                        issues.append(Issue(
                            check=self.name,
                            file=str(src_file.relative_to(root)),
                            detail=f"potential {label}: '{val[:40]}...'",
                            severity="error",
                        ))

        return issues


class DeadCodeCheck:
    """Flag Python modules with zero imports from the rest of the codebase."""

    name = "dead_code"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        src_dir = root / "src"
        if not src_dir.exists():
            return issues

        py_files = [f for f in src_dir.rglob("*.py") if f.name != "__init__.py" and not config.is_ignored(f)]

        all_source = ""
        init_source = ""
        for py_file in py_files:
            try:
                all_source += py_file.read_text(encoding="utf-8") + "\n"
            except Exception:
                pass
        # Also read all __init__.py files — re-exports count as imports
        for init_file in src_dir.rglob("__init__.py"):
            try:
                init_source += init_file.read_text(encoding="utf-8") + "\n"
            except Exception:
                pass

        for py_file in py_files:
            rel = py_file.relative_to(src_dir)
            module_parts = list(rel.with_suffix("").parts)
            module_name = ".".join(module_parts)
            file_name = py_file.name.replace(".py", "")

            import_patterns = [f"from {module_name}", f"import {module_name}"]
            if len(module_parts) > 1:
                parent = ".".join(module_parts[:-1])
                import_patterns.append(f"from {parent} import {file_name}")
                # Also check relative imports
                import_patterns.append(f"from .{file_name}")
                import_patterns.append(f"from . import {file_name}")

            imported = any(p in all_source for p in import_patterns)
            if not imported:
                imported = any(p in init_source for p in import_patterns)

            if not imported:
                test_file = root / "tests" / f"test_{py_file.name}"
                has_tests = test_file.exists()
                if not has_tests:
                    issues.append(Issue(
                        check=self.name,
                        file=str(py_file.relative_to(root)),
                        detail=f"module '{module_name}' has zero imports and zero tests",
                        severity="warn",
                    ))

        return issues


class TestCoverageCheck:
    """Verify every source module has a corresponding test file."""

    name = "test_coverage"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        src_dir = root / "src"
        tests_dir = root / "tests"

        if not src_dir.exists() or not tests_dir.exists():
            return issues

        for py_file in src_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            if config.is_ignored(py_file):
                continue

            test_file = tests_dir / f"test_{py_file.name}"
            if not test_file.exists():
                issues.append(Issue(
                    check=self.name,
                    file=str(py_file.relative_to(root)),
                    detail=f"no test file for {py_file.name} (expected tests/test_{py_file.name})",
                    severity="warn",
                ))

        return issues


class CliOutputCheck:
    """Verify CLI output (especially init) mentions all canonical files."""

    name = "cli_output"

    _REQUIRED_MENTIONS = [
        "AGENTS.md",
        "dangerous_patterns.toml",
        "session-protocol.md",
        "project-conductor.md",
    ]

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        cli_file = root / "src" / "drifter" / "cli.py"
        if not cli_file.exists():
            return issues

        cli_text = cli_file.read_text(encoding="utf-8")
        init_match = re.search(r"def cmd_init\([^)]*\):(.*?)(?=\ndef |\nclass |\Z)", cli_text, re.DOTALL)
        if not init_match:
            return issues

        init_text = init_match.group(1)
        for mention in self._REQUIRED_MENTIONS:
            if mention not in init_text:
                issues.append(Issue(
                    check=self.name,
                    file="src/drifter/cli.py",
                    detail=f"cmd_init output does not mention '{mention}'",
                    severity="warn",
                ))

        return issues


class GitignoreCheck:
    """Verify sensitive file patterns from dangerous_patterns.toml are in .gitignore if files exist."""

    name = "gitignore"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        gitignore = root / ".gitignore"

        if not gitignore.exists():
            issues.append(Issue(
                check=self.name,
                file=".gitignore",
                detail=".gitignore does not exist",
                severity="warn",
            ))
            return issues

        gitignore_text = gitignore.read_text(encoding="utf-8")
        lines = [line.strip() for line in gitignore_text.split("\n") if line.strip() and not line.strip().startswith("#")]

        patterns_file = root / "dangerous_patterns.toml"
        sensitive_patterns: list[str] = [".env", "*.key", "*.pem", "id_rsa*"]
        if patterns_file.exists():
            try:
                with patterns_file.open("rb") as f:
                    data = tomllib.load(f)
                sensitive_patterns = data.get("filesystem", {}).get("sensitive_patterns", sensitive_patterns)
            except Exception:
                pass

        for pattern in sensitive_patterns:
            matches = list(root.rglob(pattern))
            if matches:
                # Check if pattern or a close variant is in .gitignore
                normalized = pattern.replace("*", "")
                in_gitignore = any(
                    pattern in line or normalized in line
                    for line in lines
                )
                if not in_gitignore:
                    issues.append(Issue(
                        check=self.name,
                        file=".gitignore",
                        detail=f"sensitive file pattern '{pattern}' exists in repo but not in .gitignore",
                        severity="error",
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
        active_match = re.search(r"\*\*ID\*\*\s*\|\s*(.+?)\s*\n", text)
        if active_match:
            active_id = active_match.group(1).strip()
            if active_id != "—":
                active_ids.add(active_id)
                all_ids.add(active_id)

        # Extract IDs from Blocked Tasks table
        blocked_section = re.search(r"## Blocked Tasks.*?(?=## |\Z)", text, re.DOTALL)
        if blocked_section:
            for line in blocked_section.group(0).split("\n"):
                if line.strip().startswith("|") and "ID" not in line and "---" not in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 2 and parts[1] and parts[1] != "—":
                        blocked_ids.add(parts[1])
                        all_ids.add(parts[1])

        # Extract IDs from Future Tasks table
        future_section = re.search(r"## Future Tasks.*?(?=## |\Z)", text, re.DOTALL)
        if future_section:
            for line in future_section.group(0).split("\n"):
                if line.strip().startswith("|") and "ID" not in line and "---" not in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 2 and parts[1] and parts[1] != "—":
                        future_ids.add(parts[1])
                        all_ids.add(parts[1])

        # Extract IDs from Completed Tasks table
        completed_section = re.search(r"## Completed Tasks.*?(?=## |\Z)", text, re.DOTALL)
        if completed_section:
            for line in completed_section.group(0).split("\n"):
                if line.strip().startswith("|") and "ID" not in line and "---" not in line:
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
        depends_on_pattern = re.compile(r"\*\*Depends On\*\*\s*\|\s*(.+?)\s*\n")
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
            id_match = re.search(r"\*\*ID\*\*\s*\|\s*(.+?)\s*\n", preceding)
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
                    if line.strip().startswith("|") and "ID" not in line and "---" not in line:
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
                if line.strip().startswith("|") and "ID" not in line and "---" not in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 6 and parts[1] and parts[1] != "—":
                        blocked_on = parts[5] if len(parts) > 5 else ""
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
                if line.strip().startswith("|") and "ID" not in line and "---" not in line:
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


class TomllibCompatibilityCheck:
    """Scan for bare 'import tomllib' without Python 3.11 version guard."""

    name = "tomllib_compatibility"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        src_dir = root / "src"
        if not src_dir.exists():
            return issues

        for py_file in src_dir.rglob("*.py"):
            if config.is_ignored(py_file):
                continue
            text = py_file.read_text(encoding="utf-8")
            if "import tomllib" not in text:
                continue
            # If the file has a version guard, it's safe
            if "sys.version_info" in text and "tomli as tomllib" in text:
                continue
            # If the file imports tomli as tomllib unconditionally (like shell_guard.py at module level)
            # that's also acceptable as long as there's a version guard somewhere
            if "import tomli as tomllib" in text:
                continue
            issues.append(Issue(
                check=self.name,
                file=str(py_file.relative_to(root)),
                detail="bare 'import tomllib' found without Python 3.11 version guard — will crash on Python 3.10",
                severity="error",
            ))
        return issues


class AuditCoverageCheck:
    """Verify cmd_audit handles all ShellGuard action types."""

    name = "audit_coverage"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        cli_file = root / "src" / "drifter" / "cli.py"
        shell_guard_file = root / "src" / "drifter" / "shell_guard.py"

        if not cli_file.exists() or not shell_guard_file.exists():
            return issues

        cli_text = cli_file.read_text(encoding="utf-8")
        shell_text = shell_guard_file.read_text(encoding="utf-8")

        # Find all action types returned by ShellGuard
        action_values = set(re.findall(r'action="(\w+)"', shell_text))
        # Exclude 'allow' since audit doesn't need to report allowed commands
        action_values.discard("allow")

        # Find cmd_audit function
        audit_match = re.search(r"def cmd_audit\(.*?\n(?=\ndef |\nclass |\Z)", cli_text, re.DOTALL)
        if not audit_match:
            return issues

        audit_text = audit_match.group(0)
        for action in action_values:
            if f'"{action}"' not in audit_text:
                issues.append(Issue(
                    check=self.name,
                    file="src/drifter/cli.py",
                    detail=f"cmd_audit does not handle ShellGuard action '{action}'",
                    severity="error",
                ))

        return issues


class ReporterCompletenessCheck:
    """Verify console reporter handles all severity levels explicitly."""

    name = "reporter_completeness"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        cli_file = root / "src" / "drifter" / "cli.py"
        if not cli_file.exists():
            return issues

        cli_text = cli_file.read_text(encoding="utf-8")

        # Find console formatter
        formatter_match = re.search(
            r"def _format_issues_console\(.*?\n(?=\ndef |\nclass |\Z)", cli_text, re.DOTALL
        )
        if not formatter_match:
            return issues

        formatter_text = formatter_match.group(0)
        severities = ["error", "warn", "info"]
        for sev in severities:
            if sev not in formatter_text:
                issues.append(Issue(
                    check=self.name,
                    file="src/drifter/cli.py",
                    detail=f"_format_issues_console() does not reference severity '{sev}'",
                    severity="error",
                ))

        return issues


class TemplateCountSyncCheck:
    """Verify hardcoded counts in templates match actual code counts."""

    name = "template_count_sync"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        template_dir = root / "templates"
        if not template_dir.exists():
            return issues

        drift_guard = root / "src" / "drifter" / "drift_guard.py"
        actual_checks = 0
        if drift_guard.exists():
            guard_text = drift_guard.read_text(encoding="utf-8")
            actual_checks = len(re.findall(r"class \w+Check:", guard_text))

        preflight_file = root / "src" / "drifter" / "pre_flight.py"
        actual_steps = 0
        if preflight_file.exists():
            preflight_text = preflight_file.read_text(encoding="utf-8")
            actual_steps = len(re.findall(r"# Step \d+:", preflight_text))

        for tmpl_file in template_dir.glob("*.tmpl"):
            if config.is_ignored(tmpl_file):
                continue
            text = tmpl_file.read_text(encoding="utf-8")
            rel = str(tmpl_file.relative_to(root))

            # Check "Built-in checks (N total)"
            check_count_match = re.search(r"Built-in checks \((\d+) total\)", text)
            if check_count_match and actual_checks > 0:
                listed = int(check_count_match.group(1))
                if listed != actual_checks:
                    issues.append(Issue(
                        check=self.name,
                        file=rel,
                        detail=f"claims {listed} built-in checks but drift_guard.py has {actual_checks}",
                        severity="warn",
                    ))

            # Check "N-step pre-flight"
            step_match = re.search(r"(\d+)-step pre-flight", text, re.IGNORECASE)
            if step_match and actual_steps > 0:
                listed = int(step_match.group(1))
                if listed != actual_steps:
                    issues.append(Issue(
                        check=self.name,
                        file=rel,
                        detail=f"claims {listed}-step pre-flight but pre_flight.py has {actual_steps} steps",
                        severity="warn",
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
    "timestamp_staleness": TimestampStalenessCheck,
    "conductor_content": ConductorContentCheck,
    "architecture_doc_sync": ArchitectureDocSyncCheck,
    "readme_completeness": ReadmeCompletenessCheck,
    "pre_flight_sync": PreFlightSyncCheck,
    "credential_leak": CredentialLeakCheck,
    "dead_code": DeadCodeCheck,
    "test_coverage": TestCoverageCheck,
    "cli_output": CliOutputCheck,
    "gitignore": GitignoreCheck,
    "pipeline_integrity": PipelineIntegrityCheck,
    "archive_integrity": ArchiveIntegrityCheck,
    "tomllib_compatibility": TomllibCompatibilityCheck,
    "audit_coverage": AuditCoverageCheck,
    "reporter_completeness": ReporterCompletenessCheck,
    "template_count_sync": TemplateCountSyncCheck,
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

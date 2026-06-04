from __future__ import annotations

import re
from pathlib import Path

from drifter._toml_utils import safe_load_toml
from drifter.checks._base import Check, Issue
from drifter.config import Config

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
        (re.compile(r"https?://[^:]+:[^@]+@"), "URL with embedded credentials"),
        (re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"), "Private key block"),
        (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID"),
        (re.compile(r"[A-Za-z0-9/+=]{40}"), "Base64-like high-entropy string (possible secret)"),
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
        data = safe_load_toml(patterns_file)
        if data is None:
            issues.append(Issue(
                check=self.name,
                file="dangerous_patterns.toml",
                detail="Invalid TOML in dangerous_patterns.toml",
                severity="error",
            ))
            return issues
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
            data = safe_load_toml(patterns_file)
            if data is not None:
                sensitive_patterns = data.get("filesystem", {}).get("sensitive_patterns", sensitive_patterns)

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

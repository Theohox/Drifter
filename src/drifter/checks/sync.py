from __future__ import annotations

import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    pass
else:
    pass

from drifter.checks._base import Issue
from drifter.config import Config


class ArchitectureDocSyncCheck:
    """Verify architecture.md reflects current number of checks and CLI commands."""

    name = "architecture_doc_sync"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        arch_file = root / "docs" / "architecture.md"
        if not arch_file.exists():
            return issues

        arch_text = arch_file.read_text(encoding="utf-8")

        # Count check classes across all check modules
        checks_dir = root / "src" / "drifter" / "checks"
        actual_checks = 0
        if checks_dir.exists():
            for check_file in checks_dir.glob("*.py"):
                if check_file.name.startswith("_"):
                    continue
                check_text = check_file.read_text(encoding="utf-8")
                actual_checks += len(re.findall(r"class \w+Check:", check_text))
        # Also check legacy drift_guard.py
        drift_guard = root / "src" / "drifter" / "drift_guard.py"
        if drift_guard.exists():
            guard_text = drift_guard.read_text(encoding="utf-8")
            actual_checks += len(re.findall(r"class \w+Check:", guard_text))

        listed_checks = len(re.findall(r"•\s+\w+Check", arch_text))
        if listed_checks > 0 and actual_checks != listed_checks:
            issues.append(
                Issue(
                    check=self.name,
                    file="docs/architecture.md",
                    detail=f"lists {listed_checks} checks but checks package has {actual_checks}",
                    severity="warn",
                )
            )

        cli_file = root / "src" / "drifter" / "cli.py"
        if cli_file.exists():
            cli_text = cli_file.read_text(encoding="utf-8")
            actual_commands = len(
                re.findall(r'subparsers\.add_parser\(\s*"([^"]+)"', cli_text)
            )
            listed_commands = len(re.findall(r"`drifter [\w-]+`", arch_text))
            if listed_commands > 0 and actual_commands != listed_commands:
                issues.append(
                    Issue(
                        check=self.name,
                        file="docs/architecture.md",
                        detail=f"lists {listed_commands} CLI commands but cli.py has {actual_commands}",
                        severity="warn",
                    )
                )

        # Check templates/drifter.toml.tmpl for hardcoded check counts
        toml_tmpl = root / "templates" / "drifter.toml.tmpl"
        if toml_tmpl.exists():
            toml_text = toml_tmpl.read_text(encoding="utf-8")
            check_count_match = re.search(r"Built-in checks \((\d+) total\)", toml_text)
            if check_count_match:
                listed = int(check_count_match.group(1))
                if listed != actual_checks:
                    issues.append(
                        Issue(
                            check=self.name,
                            file="templates/drifter.toml.tmpl",
                            detail=f"claims {listed} built-in checks but checks package has {actual_checks}",
                            severity="warn",
                        )
                    )

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
        for match in re.finditer(
            r"(\d+)-step pre-flight", preflight_text, re.IGNORECASE
        ):
            listed = int(match.group(1))
            if listed != preflight_steps:
                issues.append(
                    Issue(
                        check=self.name,
                        file="src/drifter/pre_flight.py",
                        detail=f"docstring claims {listed}-step pre-flight but file has {preflight_steps} steps",
                        severity="warn",
                    )
                )
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

            if (
                preflight_steps != protocol_steps
                and preflight_steps > 0
                and protocol_steps > 0
            ):
                issues.append(
                    Issue(
                        check=self.name,
                        file="docs/session-protocol.md",
                        detail=f"pre_flight.py has {preflight_steps} steps but protocol lists {protocol_steps}",
                        severity="warn",
                    )
                )

            dp_in_protocol = "dangerous_patterns.toml" in protocol_text
            if not dp_in_protocol:
                issues.append(
                    Issue(
                        check=self.name,
                        file="docs/session-protocol.md",
                        detail="does not mention dangerous_patterns.toml in pre-flight steps",
                        severity="warn",
                    )
                )

        # Check methodology.md for step count consistency
        methodology_file = root / "docs" / "methodology.md"
        if methodology_file.exists():
            methodology_text = methodology_file.read_text(encoding="utf-8")
            for match in re.finditer(
                r"(\d+)-step pre-flight", methodology_text, re.IGNORECASE
            ):
                listed = int(match.group(1))
                if listed != preflight_steps:
                    issues.append(
                        Issue(
                            check=self.name,
                            file="docs/methodology.md",
                            detail=f"claims {listed}-step pre-flight but pre_flight.py has {preflight_steps} steps",
                            severity="warn",
                        )
                    )
                    break

        # Check README.md for step count consistency
        readme_file = root / "README.md"
        if readme_file.exists():
            readme_text = readme_file.read_text(encoding="utf-8")
            for match in re.finditer(
                r"(\d+)-step pre-flight", readme_text, re.IGNORECASE
            ):
                listed = int(match.group(1))
                if listed != preflight_steps:
                    issues.append(
                        Issue(
                            check=self.name,
                            file="README.md",
                            detail=f"claims {listed}-step pre-flight but pre_flight.py has {preflight_steps} steps",
                            severity="warn",
                        )
                    )
                    break

        dp_in_preflight = "dangerous_patterns.toml" in preflight_text
        if not dp_in_preflight:
            issues.append(
                Issue(
                    check=self.name,
                    file="src/drifter/pre_flight.py",
                    detail="does not verify dangerous_patterns.toml exists",
                    severity="warn",
                )
            )

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
            issues.append(
                Issue(
                    check=self.name,
                    file="README.md",
                    detail="README.md does not exist",
                    severity="warn",
                )
            )
            return issues

        # If README predates Drifter installation, be lenient — the user may not
        # have updated it yet. Only enforce if README is newer than drifter files.
        readme_mtime = readme.stat().st_mtime
        drifter_files = [
            root / "drifter.toml",
            root / "AGENTS.md",
            root / "docs" / "session-protocol.md",
        ]
        drifter_mtime = None
        for df in drifter_files:
            if df.exists():
                mt = df.stat().st_mtime
                if drifter_mtime is None or mt < drifter_mtime:
                    drifter_mtime = mt

        # If README is older than drifter files, user hasn't updated it yet — skip
        if drifter_mtime is not None and readme_mtime < drifter_mtime:
            return issues

        text = readme.read_text(encoding="utf-8")
        for mention in self._REQUIRED_MENTIONS:
            if mention not in text:
                issues.append(
                    Issue(
                        check=self.name,
                        file="README.md",
                        detail=f"does not mention '{mention}'",
                        severity="warn",
                    )
                )

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
        init_match = re.search(
            r"def cmd_init\([^)]*\):(.*?)(?=\ndef |\nclass |\Z)", cli_text, re.DOTALL
        )
        if not init_match:
            return issues

        init_text = init_match.group(1)
        for mention in self._REQUIRED_MENTIONS:
            if mention not in init_text:
                issues.append(
                    Issue(
                        check=self.name,
                        file="src/drifter/cli.py",
                        detail=f"cmd_init output does not mention '{mention}'",
                        severity="warn",
                    )
                )

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
        audit_match = re.search(
            r"def cmd_audit\(.*?\n(?=\ndef |\nclass |\Z)", cli_text, re.DOTALL
        )
        if not audit_match:
            return issues

        audit_text = audit_match.group(0)
        for action in action_values:
            if f'"{action}"' not in audit_text:
                issues.append(
                    Issue(
                        check=self.name,
                        file="src/drifter/cli.py",
                        detail=f"cmd_audit does not handle ShellGuard action '{action}'",
                        severity="error",
                    )
                )

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
            r"def _format_issues_console\(.*?\n(?=\ndef |\nclass |\Z)",
            cli_text,
            re.DOTALL,
        )
        if not formatter_match:
            return issues

        formatter_text = formatter_match.group(0)
        severities = ["error", "warn", "info"]
        for sev in severities:
            if sev not in formatter_text:
                issues.append(
                    Issue(
                        check=self.name,
                        file="src/drifter/cli.py",
                        detail=f"_format_issues_console() does not reference severity '{sev}'",
                        severity="error",
                    )
                )

        return issues


class DocCoverageCheck:
    """Verify AGENTS.md documents all modules, CLI commands, and features.

    Also verify README.md mentions key features, and that config/template
    files are in sync with their templates.
    """

    name = "doc_coverage"

    # Files that should match their templates exactly
    _TEMPLATE_PAIRS = [
        ("dangerous_patterns.toml", "templates/dangerous_patterns.toml.tmpl"),
    ]

    # Key features that should be mentioned in README.md
    _README_FEATURES = [
        "enforcement",
        "dangerous_patterns",
        "session audit",
        "pre-flight",
        "conductor",
    ]

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []

        # --- 1. AGENTS.md module coverage ---
        agents_md = root / "AGENTS.md"
        if agents_md.exists():
            agents_text = agents_md.read_text(encoding="utf-8")
            src_dir = root / "src" / "drifter"
            if src_dir.exists():
                for py_file in src_dir.glob("*.py"):
                    if py_file.name in ("__init__.py", "_base.py"):
                        continue
                    # Skip private helper modules (e.g., _doc_validate.py, _conductor_helpers.py)
                    if py_file.name.startswith("_"):
                        continue
                    module_name = py_file.name
                    if module_name not in agents_text:
                        issues.append(
                            Issue(
                                check=self.name,
                                file="AGENTS.md",
                                detail=f"does not mention module '{module_name}'",
                                severity="warn",
                            )
                        )

        # --- 2. AGENTS.md Quick Reference CLI coverage ---
        cli_file = root / "src" / "drifter" / "cli.py"
        if cli_file.exists() and agents_md.exists():
            cli_text = cli_file.read_text(encoding="utf-8")
            # Extract top-level subparser commands (exclude conductor_sub)
            commands = re.findall(
                r'(?<!conductor_sub\.)add_parser\("([^"]+)"', cli_text
            )
            # Also extract conductor sub-commands
            conductor_subs = re.findall(
                r'conductor_sub\.add_parser\("([^"]+)"', cli_text
            )
            for cmd in commands:
                if f"drifter {cmd}" not in agents_text:
                    issues.append(
                        Issue(
                            check=self.name,
                            file="AGENTS.md",
                            detail=f"Quick Reference missing CLI command 'drifter {cmd}'",
                            severity="warn",
                        )
                    )
            for cmd in conductor_subs:
                if f"drifter conductor {cmd}" not in agents_text:
                    issues.append(
                        Issue(
                            check=self.name,
                            file="AGENTS.md",
                            detail=f"Quick Reference missing CLI command 'drifter conductor {cmd}'",
                            severity="warn",
                        )
                    )

        # --- 3. README.md feature coverage ---
        readme = root / "README.md"
        if readme.exists():
            readme_text = readme.read_text(encoding="utf-8").lower()
            for feature in self._README_FEATURES:
                if feature.lower() not in readme_text:
                    issues.append(
                        Issue(
                            check=self.name,
                            file="README.md",
                            detail=f"does not mention feature '{feature}'",
                            severity="warn",
                        )
                    )

        # --- 4. Template sync ---
        for rendered_name, template_name in self._TEMPLATE_PAIRS:
            rendered = root / rendered_name
            template = root / template_name
            if rendered.exists() and template.exists():
                if rendered.read_text(encoding="utf-8") != template.read_text(
                    encoding="utf-8"
                ):
                    issues.append(
                        Issue(
                            check=self.name,
                            file=rendered_name,
                            detail=f"diverges from template '{template_name}'",
                            severity="warn",
                        )
                    )

        return issues

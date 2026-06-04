"""Capability manifest generator.

Scans the Drifter codebase and emits a machine-readable manifest of
checks, commands, reporters, MCP tools, and document types.

The manifest is the single source of truth for what Drifter can do.
Claims in docs (README, AGENTS.md, SOWs) can be validated against it.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from drifter._toml_utils import safe_load_toml


@dataclass
class CommandInfo:
    name: str
    help: str


@dataclass
class CheckInfo:
    name: str
    module: str
    description: str = ""
    severity: str = "warn"


@dataclass
class McpToolInfo:
    name: str
    description: str


@dataclass
class ReporterInfo:
    name: str
    module: str


@dataclass
class CapabilityManifest:
    version: str
    commands: list[CommandInfo] = field(default_factory=list)
    checks: list[CheckInfo] = field(default_factory=list)
    mcp_tools: list[McpToolInfo] = field(default_factory=list)
    reporters: list[ReporterInfo] = field(default_factory=list)
    doc_types: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "commands": [asdict(c) for c in self.commands],
            "checks": [asdict(c) for c in self.checks],
            "mcp_tools": [asdict(t) for t in self.mcp_tools],
            "reporters": [asdict(r) for r in self.reporters],
            "doc_types": sorted(self.doc_types),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


def _extract_version(root: Path) -> str:
    """Read version from pyproject.toml."""
    pyproject = root / "pyproject.toml"
    data = safe_load_toml(pyproject)
    if data is None:
        return "unknown"
    return data.get("project", {}).get("version", "unknown")


def _scan_cli_commands(root: Path) -> list[CommandInfo]:
    """Parse cli.py for subparser names and help text."""
    cli_file = root / "src" / "drifter" / "cli.py"
    if not cli_file.exists():
        return []

    text = cli_file.read_text(encoding="utf-8")
    commands: list[CommandInfo] = []

    # Match: subparsers.add_parser("name", help="...")
    # or multi-line: subparsers.add_parser(
    #     "name",
    #     help="...",
    # )
    single_line = re.findall(
        r'subparsers\.add_parser\(\s*"([^"]+)"(?:\s*,\s*help\s*=\s*"([^"]*)")?',
        text,
    )
    for name, help_text in single_line:
        commands.append(CommandInfo(name=name, help=help_text))

    # Multi-line conductor sub-commands
    conductor = re.findall(
        r'conductor_sub\.add_parser\(\s*"([^"]+)"(?:\s*,\s*help\s*=\s*"([^"]*)")?',
        text,
    )
    for name, help_text in conductor:
        commands.append(CommandInfo(name=f"conductor {name}", help=help_text))

    return commands


def _scan_checks(root: Path) -> list[CheckInfo]:
    """Read BUILTIN_CHECKS from checks/__init__.py and extract descriptions/severities."""
    init_file = root / "src" / "drifter" / "checks" / "__init__.py"
    checks_dir = root / "src" / "drifter" / "checks"
    if not init_file.exists():
        return []

    text = init_file.read_text(encoding="utf-8")
    checks: list[CheckInfo] = []

    # Extract the BUILTIN_CHECKS dict
    match = re.search(r"BUILTIN_CHECKS:\s*dict\[.*?\]\s*=\s*\{(.*?)\}", text, re.DOTALL)
    if not match:
        return checks

    body = match.group(1)
    name_to_module: dict[str, str] = {}
    for line in body.split("\n"):
        m = re.search(r'"([^"]+)"\s*:\s*(\w+)', line)
        if m:
            name_to_module[m.group(1)] = m.group(2)

    # Parse all check module files to extract docstrings
    class_docstrings: dict[str, str] = {}
    if checks_dir.exists():
        for py_file in checks_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name.endswith("Check"):
                        doc = ast.get_docstring(node) or ""
                        class_docstrings[node.name] = doc.split("\n")[0].strip()
            except Exception:
                pass

    # Look up severities from DEFAULT_CONFIG
    severities: dict[str, str] = {}
    try:
        from drifter.config import DEFAULT_CONFIG

        for check_cfg in DEFAULT_CONFIG.get("checks", []):
            severities[check_cfg["name"]] = check_cfg.get("severity", "warn")
    except Exception:
        pass

    for check_name, class_name in name_to_module.items():
        checks.append(
            CheckInfo(
                name=check_name,
                module=class_name,
                description=class_docstrings.get(class_name, ""),
                severity=severities.get(check_name, "warn"),
            )
        )

    return checks


def _scan_mcp_tools(root: Path) -> list[McpToolInfo]:
    """Extract @mcp.tool() decorated functions from server.py."""
    server_file = root / "plugins" / "mcp-server" / "server.py"
    if not server_file.exists():
        return []

    tree = ast.parse(server_file.read_text(encoding="utf-8"))
    tools: list[McpToolInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                # Match @mcp.tool() or @mcp_tool()
                is_mcp_tool = False
                if isinstance(decorator, ast.Attribute) and decorator.attr == "tool":
                    is_mcp_tool = True
                elif (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr == "tool"
                ):
                    is_mcp_tool = True
                elif isinstance(decorator, ast.Name) and decorator.id == "mcp_tool":
                    is_mcp_tool = True
                elif (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Name)
                    and decorator.func.id == "mcp_tool"
                ):
                    is_mcp_tool = True

                if is_mcp_tool:
                    docstring = ast.get_docstring(node) or ""
                    tools.append(
                        McpToolInfo(
                            name=node.name,
                            description=docstring.split("\n")[0].strip()
                            if docstring
                            else "",
                        )
                    )
                    break

    return tools


def _scan_reporters(root: Path) -> list[ReporterInfo]:
    """List reporter classes in reporters/ directory."""
    reporters_dir = root / "src" / "drifter" / "reporters"
    if not reporters_dir.exists():
        return []

    reporters: list[ReporterInfo] = []
    for py_file in reporters_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        text = py_file.read_text(encoding="utf-8")
        for match in re.finditer(r"class\s+(\w+Reporter)", text):
            reporters.append(ReporterInfo(name=match.group(1), module=py_file.stem))

    return reporters


def _scan_doc_types(root: Path) -> list[str]:
    """Read VALID_TYPES from _doc_validate.py."""
    doc_validate = root / "src" / "drifter" / "_doc_validate.py"
    if not doc_validate.exists():
        return []

    text = doc_validate.read_text(encoding="utf-8")
    match = re.search(r"VALID_TYPES\s*=\s*\{(.*?)\}", text, re.DOTALL)
    if not match:
        return []

    types: list[str] = []
    for line in match.group(1).split("\n"):
        m = re.search(r'"([^"]+)"', line)
        if m:
            types.append(m.group(1))
    return types


def generate_manifest(root: Path | None = None) -> CapabilityManifest:
    """Scan the codebase and return a CapabilityManifest."""
    if root is None:
        root = Path(".").resolve()

    return CapabilityManifest(
        version=_extract_version(root),
        commands=_scan_cli_commands(root),
        checks=_scan_checks(root),
        mcp_tools=_scan_mcp_tools(root),
        reporters=_scan_reporters(root),
        doc_types=_scan_doc_types(root),
    )


def write_manifest(root: Path | None = None) -> Path:
    """Generate and write the manifest to .drifter/capability-manifest.json."""
    if root is None:
        root = Path(".").resolve()

    manifest = generate_manifest(root)
    output = root / ".drifter" / "capability-manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(manifest.to_json(), encoding="utf-8")
    return output


# ---------------------------------------------------------------------------
# describe — human/machine-readable project description
# ---------------------------------------------------------------------------


def describe_json(root: Path | None = None) -> str:
    """Return a JSON description of the project."""
    manifest = generate_manifest(root)
    return json.dumps(
        {
            "version": manifest.version,
            "checks": len(manifest.checks),
            "commands": [
                {"name": c.name, "description": c.help} for c in manifest.commands
            ],
            "mcp_tools": [
                {"name": t.name, "description": t.description}
                for t in manifest.mcp_tools
            ],
            "doc_types": sorted(manifest.doc_types),
            "features": {
                "suppression": True,
                "hmac_audit": True,
            },
        },
        indent=2,
    )


def describe_markdown(root: Path | None = None) -> str:
    """Return a Markdown description of the project."""
    manifest = generate_manifest(root)
    lines = [
        f"# Drifter {manifest.version} — Capability Overview",
        "",
        "## CLI Commands",
        "",
        "| Command | Description |",
        "|---------|-------------|",
    ]
    for cmd in manifest.commands:
        lines.append(f"| `{cmd.name}` | {cmd.help or '—'} |")

    lines.extend(
        [
            "",
            "## Checks",
            "",
            f"**{len(manifest.checks)} built-in drift checks:**",
            "",
            "| Check | Description | Severity |",
            "|-------|-------------|----------|",
        ]
    )
    for check in manifest.checks:
        lines.append(
            f"| `{check.name}` | {check.description or '—'} | {check.severity} |"
        )

    lines.extend(
        [
            "",
            "## MCP Tools",
            "",
        ]
    )
    for tool in manifest.mcp_tools:
        lines.append(f"- `{tool.name}` — {tool.description or '—'}")

    lines.extend(
        [
            "",
            "## Document Types",
            "",
            ", ".join(f"`{t}`" for t in sorted(manifest.doc_types)),
            "",
            "## Features",
            "",
            "- Per-check suppression (`ignore_paths`, `ignore_patterns`)",
            "- HMAC-signed tamper-evident session audit logs",
            "- Git pre-commit hook integration",
            "",
        ]
    )

    return "\n".join(lines)

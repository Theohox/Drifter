"""Detect hallucinated references to Drifter commands and MCP tools in docs."""

from __future__ import annotations

import json
import re
from pathlib import Path

from drifter.checks._base import Issue
from drifter.config import Config


def _load_manifest(root: Path) -> dict | None:
    manifest_path = root / ".drifter" / "capability-manifest.json"
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _generate_manifest(root: Path) -> dict | None:
    try:
        from drifter.manifest_generator import generate_manifest

        cap = generate_manifest(root)
        if hasattr(cap, "to_dict"):
            return cap.to_dict()
        return cap if isinstance(cap, dict) else None
    except Exception:
        return None


def _get_valid_commands(manifest: dict) -> set[str]:
    return {cmd["name"] for cmd in manifest.get("commands", [])}


def _get_valid_mcp_tools(manifest: dict) -> set[str]:
    return {tool["name"] for tool in manifest.get("mcp_tools", [])}


# Patterns that look like drifter command references
_RE_DRIFTER_CMD = re.compile(r"`drifter\s+(\w+)`")
_RE_DRIFTER_CMD_LOOSE = re.compile(r"\bdrifter\s+(\w+)\b")
_RE_MCP_TOOL = re.compile(r"\b(drifter_\w+)\b")


class GhostReferenceCheck:
    """Scan markdown docs for references to non-existent commands or MCP tools."""

    name = "ghost_reference"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []

        manifest = _load_manifest(root)
        if manifest is None:
            manifest = _generate_manifest(root)
        if manifest is None:
            return issues

        valid_commands = _get_valid_commands(manifest)
        valid_mcp_tools = _get_valid_mcp_tools(manifest)

        # Scan markdown files
        md_files = list(root.rglob("*.md"))
        # Also include root-level docs
        if (root / "README.md").exists():
            md_files.append(root / "README.md")
        md_files = list({f.resolve(): f for f in md_files}.values())

        for md_file in md_files:
            if config.is_check_ignored(self.name, md_file):
                continue
            try:
                text = md_file.read_text(encoding="utf-8")
            except Exception:
                continue

            rel = str(md_file.relative_to(root))

            # Check drifter command references (backtick inline)
            for match in _RE_DRIFTER_CMD.finditer(text):
                cmd = match.group(1)
                if cmd not in valid_commands:
                    issues.append(
                        Issue(
                            check=self.name,
                            file=rel,
                            detail=f"referenced command `drifter {cmd}` does not exist",
                            severity="warn",
                        )
                    )

            # Check MCP tool references
            for match in _RE_MCP_TOOL.finditer(text):
                tool = match.group(1)
                if tool not in valid_mcp_tools:
                    issues.append(
                        Issue(
                            check=self.name,
                            file=rel,
                            detail=f"referenced MCP tool `{tool}` does not exist",
                            severity="warn",
                        )
                    )

        return issues

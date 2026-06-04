from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from drifter._toml_utils import safe_load_toml
from drifter.checks._base import Issue
from drifter.config import Config


def _is_leaf_dict(val: dict) -> bool:
    return not any(isinstance(v, dict) for v in val.values())


def _walk_manifest_tree(manifest: dict) -> list[tuple[str, dict]]:
    """Yield (relative_path, leaf_dict) pairs from manifest [tree.*] sections."""
    results: list[tuple[str, dict]] = []

    def _collect(node: dict, path_parts: list[str]):
        for key, val in node.items():
            if isinstance(val, dict):
                if _is_leaf_dict(val):
                    try:
                        tree_idx = path_parts.index("tree")
                        prefix_parts = path_parts[tree_idx + 1 :]
                        if prefix_parts and prefix_parts[0] == "root":
                            prefix_parts = prefix_parts[1:]
                        prefix = "/".join(prefix_parts) + "/" if prefix_parts else ""
                        results.append((prefix + key, val))
                    except ValueError:
                        pass
                else:
                    _collect(val, path_parts + [key])

    _collect(manifest, [])
    return results


class TreeIntegrityCheck:
    """Verify every file on disk is declared in drifter-manifest.toml and every declared file exists."""

    name = "tree_integrity"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        manifest_file = root / "drifter-manifest.toml"
        if not manifest_file.exists():
            return issues

        manifest = safe_load_toml(manifest_file)
        if manifest is None:
            issues.append(
                Issue(
                    check=self.name,
                    file="drifter-manifest.toml",
                    detail="Cannot parse drifter-manifest.toml — file may be corrupted",
                    severity="error",
                )
            )
            return issues

        # Build declared file set from manifest tree.* sections
        declared: set[str] = set()
        for rel_path, _ in _walk_manifest_tree(manifest):
            declared.add(rel_path)

        # Walk actual tree
        actual: set[str] = set()
        for f in root.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(root))
                # Ignore standard build artifacts (match path parts, not substrings)
                parts = f.parts
                skip_parts = {
                    "__pycache__",
                    ".git",
                    "venv",
                    ".venv",
                    "node_modules",
                    ".pytest_cache",
                }
                if any(part in skip_parts for part in parts):
                    continue
                actual.add(rel)

        # Orphans: actual files not declared
        for rel in sorted(actual - declared):
            issues.append(
                Issue(
                    check=self.name,
                    file=rel,
                    detail="file exists but is not declared in drifter-manifest.toml",
                    severity="warn",
                )
            )

        # Missing: declared files not on disk
        for rel in sorted(declared - actual):
            issues.append(
                Issue(
                    check=self.name,
                    file=rel,
                    detail="declared in manifest but missing from disk",
                    severity="error",
                )
            )

        return issues


class FileSizeCheck:
    """Verify no module exceeds manifest-declared max_file_lines."""

    name = "file_size"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        manifest_file = root / "drifter-manifest.toml"
        if not manifest_file.exists():
            return issues

        manifest = safe_load_toml(manifest_file)
        if manifest is None:
            issues.append(
                Issue(
                    check=self.name,
                    file="drifter-manifest.toml",
                    detail="Cannot parse drifter-manifest.toml — file may be corrupted",
                    severity="error",
                )
            )
            return issues

        global_max = manifest.get("structure", {}).get("max_file_lines", 300)

        # Check all declared files
        for rel_path, val in _walk_manifest_tree(manifest):
            file_path = root / rel_path
            if not file_path.exists():
                continue
            if config.is_check_ignored(self.name, file_path):
                continue
            max_lines = val.get("max_lines", global_max)
            try:
                actual_lines = sum(1 for _ in file_path.open(encoding="utf-8"))
            except UnicodeDecodeError:
                # Skip binary files — they don't have "lines" in the meaningful sense
                continue
            if actual_lines > max_lines:
                issues.append(
                    Issue(
                        check=self.name,
                        file=rel_path,
                        detail=f"{actual_lines} lines exceeds max {max_lines}",
                        severity="warn",
                    )
                )

        return issues


class ManifestSyncCheck:
    """Verify BUILTIN_CHECKS count matches manifest-declared count."""

    name = "manifest_sync"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        manifest_file = root / "drifter-manifest.toml"
        if not manifest_file.exists():
            return issues

        manifest = safe_load_toml(manifest_file)
        if manifest is None:
            issues.append(
                Issue(
                    check=self.name,
                    file="drifter-manifest.toml",
                    detail="Cannot parse drifter-manifest.toml — file may be corrupted",
                    severity="error",
                )
            )
            return issues

        declared_count = manifest.get("checks", {}).get("count", 0)
        declared_names = set(manifest.get("checks", {}).get("names", []))

        # Count actual checks via AST on checks package
        checks_dir = root / "src" / "drifter" / "checks"
        actual_names: set[str] = set()
        if checks_dir.exists():
            for py_file in checks_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                try:
                    tree = ast.parse(py_file.read_text())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef) and node.name.endswith(
                            "Check"
                        ):
                            # Extract check name from class
                            for sub in ast.walk(node):
                                if isinstance(sub, ast.Assign):
                                    for target in sub.targets:
                                        if (
                                            isinstance(target, ast.Name)
                                            and target.id == "name"
                                        ):
                                            if isinstance(sub.value, ast.Constant):
                                                if isinstance(sub.value.value, str):
                                                    actual_names.add(sub.value.value)
                except Exception:
                    pass

        if declared_count != len(actual_names):
            issues.append(
                Issue(
                    check=self.name,
                    file="drifter-manifest.toml",
                    detail=f"manifest declares {declared_count} checks but checks package has {len(actual_names)}",
                    severity="error",
                )
            )

        missing = declared_names - actual_names
        if missing:
            issues.append(
                Issue(
                    check=self.name,
                    file="drifter-manifest.toml",
                    detail=f"checks declared but not found: {sorted(missing)}",
                    severity="error",
                )
            )

        extra = actual_names - declared_names
        if extra:
            issues.append(
                Issue(
                    check=self.name,
                    file="src/drifter/checks/",
                    detail=f"checks found but not declared in manifest: {sorted(extra)}",
                    severity="warn",
                )
            )

        # Validate capability manifest matches reality if it exists
        cap_manifest_path = root / ".drifter" / "capability-manifest.json"
        if cap_manifest_path.exists():
            try:
                cap_manifest = json.loads(cap_manifest_path.read_text(encoding="utf-8"))
            except Exception:
                issues.append(
                    Issue(
                        check=self.name,
                        file=".drifter/capability-manifest.json",
                        detail="cannot parse capability manifest",
                        severity="error",
                    )
                )
                return issues

            # Validate command count
            cmd_names = {cmd["name"] for cmd in cap_manifest.get("commands", [])}
            # Parse CLI for actual commands (match manifest generator logic)
            cli_file = root / "src" / "drifter" / "cli.py"
            actual_cmds: set[str] = set()
            if cli_file.exists():
                try:
                    cli_text = cli_file.read_text(encoding="utf-8")
                    for match in re.finditer(
                        r'subparsers\.add_parser\(\s*"([^"]+)"', cli_text
                    ):
                        actual_cmds.add(match.group(1))
                    for match in re.finditer(
                        r'conductor_sub\.add_parser\(\s*"([^"]+)"', cli_text
                    ):
                        actual_cmds.add(f"conductor {match.group(1)}")
                except Exception:
                    pass
            missing_cmds = actual_cmds - cmd_names
            if missing_cmds:
                issues.append(
                    Issue(
                        check=self.name,
                        file=".drifter/capability-manifest.json",
                        detail=f"commands missing from capability manifest: {sorted(missing_cmds)}",
                        severity="error",
                    )
                )
            extra_cmds = cmd_names - actual_cmds
            if extra_cmds:
                issues.append(
                    Issue(
                        check=self.name,
                        file=".drifter/capability-manifest.json",
                        detail=f"ghost commands in capability manifest: {sorted(extra_cmds)}",
                        severity="warn",
                    )
                )

            # Validate MCP tool count
            mcp_names = {tool["name"] for tool in cap_manifest.get("mcp_tools", [])}
            mcp_file = root / "plugins" / "mcp-server" / "server.py"
            actual_mcp: set[str] = set()
            if mcp_file.exists():
                try:
                    mcp_text = mcp_file.read_text(encoding="utf-8")
                    for match in re.finditer(r"def\s+(drifter_\w+)\s*\(", mcp_text):
                        actual_mcp.add(match.group(1))
                except Exception:
                    pass
            missing_mcp = actual_mcp - mcp_names
            if missing_mcp:
                issues.append(
                    Issue(
                        check=self.name,
                        file=".drifter/capability-manifest.json",
                        detail=f"MCP tools missing from capability manifest: {sorted(missing_mcp)}",
                        severity="error",
                    )
                )
            extra_mcp = mcp_names - actual_mcp
            if extra_mcp:
                issues.append(
                    Issue(
                        check=self.name,
                        file=".drifter/capability-manifest.json",
                        detail=f"ghost MCP tools in capability manifest: {sorted(extra_mcp)}",
                        severity="warn",
                    )
                )

        return issues


class ClaimSyncCheck:
    """Verify numerical claims in docs match manifest values."""

    name = "claim_sync"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        manifest_file = root / "drifter-manifest.toml"
        if not manifest_file.exists():
            return issues

        manifest = safe_load_toml(manifest_file)
        if manifest is None:
            issues.append(
                Issue(
                    check=self.name,
                    file="drifter-manifest.toml",
                    detail="Cannot parse drifter-manifest.toml — file may be corrupted",
                    severity="error",
                )
            )
            return issues

        def _resolve(path: str, data: dict) -> str | None:
            node = data
            for part in path.split("."):
                if isinstance(node, dict) and part in node:
                    node = node[part]
                else:
                    return None
            return str(node) if node is not None else None

        claims = manifest.get("claims", {})
        for doc_path, claim_list in claims.items():
            file_path = root / doc_path
            if not file_path.exists():
                issues.append(
                    Issue(
                        check=self.name,
                        file=doc_path,
                        detail="claim references file that does not exist",
                        severity="error",
                    )
                )
                continue

            text = file_path.read_text(encoding="utf-8")
            for claim in claim_list:
                pattern_template = claim.get("pattern", "")
                value_source = claim.get("value", "")

                expected = _resolve(value_source, manifest)
                if expected is None:
                    issues.append(
                        Issue(
                            check=self.name,
                            file=doc_path,
                            detail=f"claim value_source '{value_source}' not found in manifest",
                            severity="warn",
                        )
                    )
                    continue

                pattern = pattern_template.replace("{count}", r"(\d+)")
                for match in re.finditer(pattern, text):
                    found = match.group(1)
                    if found != expected:
                        issues.append(
                            Issue(
                                check=self.name,
                                file=doc_path,
                                detail=f"claim '{pattern_template}' has {found} but manifest expects {expected}",
                                severity="warn",
                            )
                        )

        return issues

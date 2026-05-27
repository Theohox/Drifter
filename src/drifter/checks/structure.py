from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from drifter.checks._base import Check, Issue
from drifter.config import Config


class TreeIntegrityCheck:
    """Verify every file on disk is declared in drifter-manifest.toml and every declared file exists."""

    name = "tree_integrity"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        manifest_file = root / "drifter-manifest.toml"
        if not manifest_file.exists():
            return issues

        with manifest_file.open("rb") as f:
            manifest = tomllib.load(f)

        # Build declared file set from manifest tree.* sections
        declared: set[str] = set()

        def _is_leaf_dict(val: dict) -> bool:
            return not any(isinstance(v, dict) for v in val.values())

        def _collect_tree(node: dict, path_parts: list[str]):
            for key, val in node.items():
                if isinstance(val, dict):
                    if _is_leaf_dict(val):
                        try:
                            tree_idx = path_parts.index("tree")
                            prefix_parts = path_parts[tree_idx + 1:]
                            if prefix_parts and prefix_parts[0] == "root":
                                prefix_parts = prefix_parts[1:]
                            prefix = "/".join(prefix_parts) + "/" if prefix_parts else ""
                            declared.add(prefix + key)
                        except ValueError:
                            pass
                    else:
                        _collect_tree(val, path_parts + [key])

        _collect_tree(manifest, [])

        # Walk actual tree
        actual: set[str] = set()
        for f in root.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(root))
                # Ignore standard build artifacts
                if any(p in rel for p in ["__pycache__", ".git", "venv", ".venv", "node_modules", ".pytest_cache"]):
                    continue
                actual.add(rel)

        # Orphans: actual files not declared
        for rel in sorted(actual - declared):
            issues.append(Issue(
                check=self.name,
                file=rel,
                detail="file exists but is not declared in drifter-manifest.toml",
                severity="warn",
            ))

        # Missing: declared files not on disk
        for rel in sorted(declared - actual):
            issues.append(Issue(
                check=self.name,
                file=rel,
                detail="declared in manifest but missing from disk",
                severity="error",
            ))

        return issues


class FileSizeCheck:
    """Verify no module exceeds manifest-declared max_file_lines."""

    name = "file_size"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        manifest_file = root / "drifter-manifest.toml"
        if not manifest_file.exists():
            return issues

        with manifest_file.open("rb") as f:
            manifest = tomllib.load(f)

        global_max = manifest.get("structure", {}).get("max_file_lines", 300)

        # Check all declared files
        def _is_leaf_dict(val: dict) -> bool:
            return not any(isinstance(v, dict) for v in val.values())

        def _check_sizes(node: dict, path_parts: list[str]):
            for key, val in node.items():
                if isinstance(val, dict):
                    if _is_leaf_dict(val):
                        try:
                            tree_idx = path_parts.index("tree")
                            prefix_parts = path_parts[tree_idx + 1:]
                            if prefix_parts and prefix_parts[0] == "root":
                                prefix_parts = prefix_parts[1:]
                            prefix = "/".join(prefix_parts) + "/" if prefix_parts else ""
                            rel_path = prefix + key
                            file_path = root / rel_path
                            if not file_path.exists():
                                continue
                            max_lines = val.get("max_lines", global_max)
                            actual_lines = sum(1 for _ in file_path.open())
                            if actual_lines > max_lines:
                                issues.append(Issue(
                                    check=self.name,
                                    file=rel_path,
                                    detail=f"{actual_lines} lines exceeds max {max_lines}",
                                    severity="warn",
                                ))
                        except ValueError:
                            pass
                    else:
                        _check_sizes(val, path_parts + [key])

        _check_sizes(manifest, [])

        return issues


class ManifestSyncCheck:
    """Verify BUILTIN_CHECKS count matches manifest-declared count."""

    name = "manifest_sync"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        manifest_file = root / "drifter-manifest.toml"
        if not manifest_file.exists():
            return issues

        with manifest_file.open("rb") as f:
            manifest = tomllib.load(f)

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
                        if isinstance(node, ast.ClassDef) and node.name.endswith("Check"):
                            # Extract check name from class
                            for sub in ast.walk(node):
                                if isinstance(sub, ast.Assign):
                                    for target in sub.targets:
                                        if isinstance(target, ast.Name) and target.id == "name":
                                            if isinstance(sub.value, ast.Constant):
                                                actual_names.add(sub.value.value)
                except Exception:
                    pass

        if declared_count != len(actual_names):
            issues.append(Issue(
                check=self.name,
                file="drifter-manifest.toml",
                detail=f"manifest declares {declared_count} checks but checks package has {len(actual_names)}",
                severity="error",
            ))

        missing = declared_names - actual_names
        if missing:
            issues.append(Issue(
                check=self.name,
                file="drifter-manifest.toml",
                detail=f"checks declared but not found: {sorted(missing)}",
                severity="error",
            ))

        extra = actual_names - declared_names
        if extra:
            issues.append(Issue(
                check=self.name,
                file="src/drifter/checks/",
                detail=f"checks found but not declared in manifest: {sorted(extra)}",
                severity="warn",
            ))

        return issues


class ClaimSyncCheck:
    """Verify numerical claims in docs match manifest values."""

    name = "claim_sync"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        manifest_file = root / "drifter-manifest.toml"
        if not manifest_file.exists():
            return issues

        with manifest_file.open("rb") as f:
            manifest = tomllib.load(f)

        check_count = manifest.get("checks", {}).get("count", 0)

        claims = manifest.get("claims", {})
        for doc_path, claim_list in claims.items():
            file_path = root / doc_path
            if not file_path.exists():
                issues.append(Issue(
                    check=self.name,
                    file=doc_path,
                    detail="claim references file that does not exist",
                    severity="error",
                ))
                continue

            text = file_path.read_text(encoding="utf-8")
            for claim in claim_list:
                pattern_template = claim.get("pattern", "")
                value_source = claim.get("value", "")

                if value_source == "checks.count":
                    expected = str(check_count)
                else:
                    continue

                pattern = pattern_template.replace("{count}", r"(\d+)")
                for match in re.finditer(pattern, text):
                    found = match.group(1)
                    if found != expected:
                        issues.append(Issue(
                            check=self.name,
                            file=doc_path,
                            detail=f"claim '{pattern_template}' has {found} but manifest expects {expected}",
                            severity="warn",
                        ))

        return issues

from __future__ import annotations

import re
from pathlib import Path

from drifter.checks._base import Issue
from drifter.checks._shared import is_skippable_path, resolve_doc_path
from drifter.config import Config


class DeadCodeCheck:
    """Flag Python modules with zero imports from the rest of the codebase."""

    name = "dead_code"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        src_dir = root / "src"
        if not src_dir.exists():
            return issues

        py_files = [
            f
            for f in src_dir.rglob("*.py")
            if f.name != "__init__.py" and not config.is_check_ignored(self.name, f)
        ]

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
                    issues.append(
                        Issue(
                            check=self.name,
                            file=str(py_file.relative_to(root)),
                            detail=f"module '{module_name}' has zero imports and zero tests",
                            severity="warn",
                        )
                    )

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
            if config.is_check_ignored(self.name, py_file):
                continue

            rel = py_file.relative_to(src_dir)
            # Accepted conventions: test_{stem}.py for top-level modules,
            # test_{parent}_{stem}.py for packaged modules
            # (e.g. test_checks_sync.py covers checks/sync.py)
            candidates = [f"test_{py_file.name}"]
            if len(rel.parts) > 1:
                candidates.append(f"test_{rel.parts[-2]}_{py_file.stem}.py")
            if any((tests_dir / name).exists() for name in candidates):
                continue

            # Fallback: any test file imports this module
            module_path = ".".join(rel.with_suffix("").parts)
            import_match = any(
                f"from {module_path} import" in text or f"import {module_path}" in text
                for test_file in tests_dir.glob("test_*.py")
                for text in [test_file.read_text(encoding="utf-8")]
            )
            if import_match:
                continue

            issues.append(
                Issue(
                    check=self.name,
                    file=str(py_file.relative_to(root)),
                    detail=f"no test file for {py_file.name} (expected {' or '.join(f'tests/{c}' for c in candidates)})",
                    severity="warn",
                )
            )

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
            if config.is_check_ignored(self.name, py_file):
                continue
            text = py_file.read_text(encoding="utf-8")
            if "import tomllib" not in text:
                continue
            # If the file has a version guard, it's safe
            if "sys.version_info" in text and "tomli as tomllib" in text:
                continue
            # An unconditional 'import tomli as tomllib' alias is also acceptable
            if "import tomli as tomllib" in text:
                continue
            issues.append(
                Issue(
                    check=self.name,
                    file=str(py_file.relative_to(root)),
                    detail="bare 'import tomllib' found without Python 3.11 version guard — will crash on Python 3.10",
                    severity="error",
                )
            )
        return issues


class HardcodedPathCheck:
    """Scan source files for hardcoded paths and verify they exist."""

    name = "hardcoded_path"

    _PATH_PATTERN = re.compile(
        r'["\']((?:docs|src|tests|config|tools|scripts|wiki|core|guides|reference)/[\w/\-\.]+)["\']'
    )

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []
        source_exts = (
            ".py",
            ".rs",
            ".js",
            ".ts",
            ".go",
            ".java",
            ".sh",
            ".toml",
            ".yaml",
            ".yml",
        )

        for ext in source_exts:
            for src_file in root.rglob(f"*{ext}"):
                if config.is_check_ignored(self.name, src_file):
                    continue
                # Skip caches, the drift engine, and test files
                str_path = str(src_file)
                if "__pycache__" in str_path or src_file.name == "drift_guard.py":
                    continue
                if "/tests/" in str_path or str_path.startswith("tests/"):
                    continue
                if not src_file.is_file():
                    continue
                try:
                    text = src_file.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                for match in self._PATH_PATTERN.finditer(text):
                    path_str = match.group(1)
                    if is_skippable_path(path_str):
                        continue
                    candidate = resolve_doc_path(root, path_str)
                    if not candidate.exists():
                        issues.append(
                            Issue(
                                check=self.name,
                                file=str(src_file.relative_to(root)),
                                detail=f"hardcodes '{path_str}' which does not exist",
                                severity="error",
                            )
                        )
        return issues

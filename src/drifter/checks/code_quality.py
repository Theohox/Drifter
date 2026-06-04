from __future__ import annotations

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

            # For check modules, look for test_checks_{stem}.py or any test that imports it
            if "src/drifter/checks/" in str(py_file):
                exact = tests_dir / f"test_checks_{py_file.stem}.py"
                if exact.exists():
                    continue
                # Fallback 1: any test_checks_* file whose name contains the stem
                name_match = any(
                    py_file.stem in f.name
                    for f in tests_dir.glob("test_checks_*.py")
                )
                if name_match:
                    continue
                # Fallback 2: any test file imports from this module
                import_path = f"drifter.checks.{py_file.stem}"
                import_match = any(
                    import_path in test_file.read_text(encoding="utf-8")
                    for test_file in tests_dir.glob("test_*.py")
                )
                if import_match:
                    continue
                issues.append(Issue(
                    check=self.name,
                    file=str(py_file.relative_to(root)),
                    detail=f"no test file for {py_file.name} (expected tests/test_checks_{py_file.stem}.py or similar)",
                    severity="warn",
                ))
            else:
                test_file = tests_dir / f"test_{py_file.name}"
                if not test_file.exists():
                    issues.append(Issue(
                        check=self.name,
                        file=str(py_file.relative_to(root)),
                        detail=f"no test file for {py_file.name} (expected tests/test_{py_file.name})",
                        severity="warn",
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
                if config.is_check_ignored(self.name, src_file):
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

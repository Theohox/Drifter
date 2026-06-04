"""Config sync check — validates config files against manifest."""

from __future__ import annotations

import re
from pathlib import Path

from drifter._toml_utils import safe_load_toml
from drifter.checks._base import Check, Issue
from drifter.config import Config


class ConfigSyncCheck:
    """Verify config.py DEFAULT_CONFIG and drifter.toml match manifest checks."""

    name = "config_sync"

    def run(self, root: Path, config: Config) -> list[Issue]:
        issues: list[Issue] = []

        manifest = root / "drifter-manifest.toml"
        if not manifest.exists():
            return issues

        data = safe_load_toml(manifest)
        if data is None:
            issues.append(Issue(
                check=self.name,
                file="drifter-manifest.toml",
                detail="Cannot parse drifter-manifest.toml — file may be corrupted",
                severity="error",
            ))
            return issues
        manifest_checks = set(data.get("checks", {}).get("names", []))

        if not manifest_checks:
            return issues

        # 1. Check config.py DEFAULT_CONFIG
        config_py = root / "src" / "drifter" / "config.py"
        if config_py.exists():
            py_checks = self._extract_py_checks(config_py)
            for check in manifest_checks - py_checks:
                issues.append(Issue(
                    check=self.name,
                    file="src/drifter/config.py",
                    detail=f"check '{check}' in manifest but missing from DEFAULT_CONFIG",
                    severity="error",
                ))
            for check in py_checks - manifest_checks:
                issues.append(Issue(
                    check=self.name,
                    file="src/drifter/config.py",
                    detail=f"check '{check}' in DEFAULT_CONFIG but not in manifest",
                    severity="error",
                ))

        # 2. Check drifter.toml
        drifter_toml = root / "drifter.toml"
        if drifter_toml.exists():
            toml_checks = self._extract_toml_checks(drifter_toml)
            for check in manifest_checks - toml_checks:
                issues.append(Issue(
                    check=self.name,
                    file="drifter.toml",
                    detail=f"check '{check}' in manifest but missing from drifter.toml",
                    severity="error",
                ))
            for check in toml_checks - manifest_checks:
                issues.append(Issue(
                    check=self.name,
                    file="drifter.toml",
                    detail=f"check '{check}' in drifter.toml but not in manifest",
                    severity="error",
                ))

        # 3. Check template (warn-only)
        template = root / "templates" / "drifter.toml.tmpl"
        if template.exists():
            tmpl_checks = self._extract_toml_checks(template)
            for check in manifest_checks - tmpl_checks:
                issues.append(Issue(
                    check=self.name,
                    file="templates/drifter.toml.tmpl",
                    detail=f"check '{check}' in manifest but missing from template",
                    severity="warn",
                ))
            for check in tmpl_checks - manifest_checks:
                issues.append(Issue(
                    check=self.name,
                    file="templates/drifter.toml.tmpl",
                    detail=f"check '{check}' in template but not in manifest",
                    severity="warn",
                ))

        return issues

    def _extract_py_checks(self, path: Path) -> set[str]:
        text = path.read_text(encoding="utf-8")
        checks_match = re.search(r'"checks":\s*\[(.*?)\]', text, re.DOTALL)
        if not checks_match:
            return set()
        return set(re.findall(r'"name":\s*"([^"]+)"', checks_match.group(1)))

    def _extract_toml_checks(self, path: Path) -> set[str]:
        data = safe_load_toml(path)
        if data is None:
            return set()
        # Support [drifter] section directly
        if "drifter" in data and isinstance(data["drifter"], dict) and "checks" in data["drifter"]:
            return {c["name"] for c in data["drifter"]["checks"] if isinstance(c, dict) and "name" in c}
        # Support [tool.drifter] nested section
        if "tool" in data and isinstance(data["tool"], dict):
            tool = data["tool"]
            if "drifter" in tool and isinstance(tool["drifter"], dict) and "checks" in tool["drifter"]:
                return {c["name"] for c in tool["drifter"]["checks"] if isinstance(c, dict) and "name" in c}
        return set()

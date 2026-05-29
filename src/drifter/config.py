"""Configuration loader for Drifter.

Resolves config from (in priority order):
1. Built-in defaults
2. drifter.toml in project root
3. pyproject.toml [tool.drifter]
4. Command-line overrides
"""

from __future__ import annotations

import fnmatch
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


DEFAULT_CONFIG: dict[str, Any] = {
    "root": ".",
    "max_pending_age_days": 7,
    "drift_threshold": 70,
    "checks": [
        {"name": "stale_reference", "enabled": True, "severity": "warn"},
        {"name": "hardcoded_path", "enabled": True, "severity": "error"},
        {"name": "digest_staleness", "enabled": True, "severity": "warn"},
        {"name": "conductor_health", "enabled": True, "severity": "error"},
        {"name": "cross_doc_consistency", "enabled": True, "severity": "warn"},
        {"name": "git_safety", "enabled": True, "severity": "error"},
        {"name": "dangerous_patterns", "enabled": True, "severity": "error"},
        {"name": "timestamp_staleness", "enabled": True, "severity": "warn"},
        {"name": "conductor_content", "enabled": True, "severity": "warn"},
        {"name": "architecture_doc_sync", "enabled": True, "severity": "warn"},
        {"name": "readme_completeness", "enabled": True, "severity": "warn"},
        {"name": "pre_flight_sync", "enabled": True, "severity": "warn"},
        {"name": "credential_leak", "enabled": True, "severity": "error"},
        {"name": "dead_code", "enabled": True, "severity": "warn"},
        {"name": "test_coverage", "enabled": True, "severity": "warn"},
        {"name": "cli_output", "enabled": True, "severity": "warn"},
        {"name": "gitignore", "enabled": True, "severity": "error"},
        {"name": "pipeline_integrity", "enabled": True, "severity": "warn"},
        {"name": "archive_integrity", "enabled": True, "severity": "error"},
        {"name": "tomllib_compatibility", "enabled": True, "severity": "error"},
        {"name": "audit_coverage", "enabled": True, "severity": "error"},
        {"name": "reporter_completeness", "enabled": True, "severity": "error"},
        {"name": "agent_self_audit", "enabled": True, "severity": "error"},
        {"name": "git_commit_approval", "enabled": True, "severity": "error"},
        {"name": "tree_integrity", "enabled": True, "severity": "warn"},
        {"name": "file_size", "enabled": True, "severity": "warn"},
        {"name": "manifest_sync", "enabled": True, "severity": "error"},
        {"name": "claim_sync", "enabled": True, "severity": "warn"},
        {"name": "read_before_write", "enabled": True, "severity": "error"},
        {"name": "test_after_write", "enabled": True, "severity": "error"},
        {"name": "drift_check_after_write", "enabled": True, "severity": "error"},
        {"name": "no_rush", "enabled": True, "severity": "warn"},
        {"name": "config_sync", "enabled": True, "severity": "error"},
    ],
    "history_path": None,
    "ignore": {
        "paths": [
            "venv/",
            ".venv/",
            "node_modules/",
            "__pycache__/",
            ".git/",
            ".tox/",
            ".pytest_cache/",
            "target/",
            "dist/",
            "build/",
        ]
    },
}


@dataclass
class CheckConfig:
    name: str
    enabled: bool = True
    severity: str = "warn"
    path: str | None = None  # optional custom check path


@dataclass
class IgnoreConfig:
    paths: list[str] = field(default_factory=list)

@dataclass
class Config:
    root: Path
    max_pending_age_days: int = 7
    drift_threshold: int = 70
    history_path: str | None = None
    checks: list[CheckConfig] = field(default_factory=list)
    ignore: IgnoreConfig = field(default_factory=IgnoreConfig)

    @classmethod
    def load(cls, root: Path | None = None, overrides: dict[str, Any] | None = None) -> Config:
        """Load configuration from defaults, files, and overrides."""
        raw = dict(DEFAULT_CONFIG)

        resolved_root = root or Path(".")
        resolved_root = resolved_root.resolve()

        # Try drifter.toml
        drifter_toml = resolved_root / "drifter.toml"
        if drifter_toml.exists():
            drifter_data = _load_toml(drifter_toml)
            # Support both [drifter] section and root-level keys
            if "drifter" in drifter_data:
                raw = _merge(raw, drifter_data["drifter"])
            else:
                raw = _merge(raw, drifter_data)

        # Try pyproject.toml [tool.drifter]
        pyproject_toml = resolved_root / "pyproject.toml"
        if pyproject_toml.exists():
            data = _load_toml(pyproject_toml)
            if "tool" in data and "drifter" in data["tool"]:
                raw = _merge(raw, data["tool"]["drifter"])

        # Apply overrides
        if overrides:
            raw = _merge(raw, overrides)

        # Build typed config
        checks = [
            CheckConfig(
                name=c["name"],
                enabled=c.get("enabled", True),
                severity=c.get("severity", "warn"),
                path=c.get("path"),
            )
            for c in raw.get("checks", [])
        ]

        return cls(
            root=resolved_root,
            max_pending_age_days=raw.get("max_pending_age_days", 7),
            drift_threshold=raw.get("drift_threshold", 70),
            history_path=raw.get("history_path"),
            checks=checks,
            ignore=IgnoreConfig(paths=raw.get("ignore", {}).get("paths", [])),
        )

    def is_ignored(self, path: Path) -> bool:
        """Check if a path matches any ignore pattern."""
        str_path = str(path)
        for pattern in self.ignore.paths:
            if fnmatch.fnmatch(str_path, pattern):
                return True
            if pattern.endswith("/"):
                dir_name = pattern.rstrip("/")
                if dir_name in path.parts or f"/{dir_name}/" in str_path or str_path.endswith(f"/{dir_name}"):
                    return True
            elif fnmatch.fnmatch(path.name, pattern):
                return True
        return False


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        return tomllib.load(f)


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge override into base."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result

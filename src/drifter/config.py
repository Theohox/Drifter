"""Configuration loader for Drifter.

Resolves config from (in priority order):
1. Built-in defaults
2. drifter.toml in project root
3. pyproject.toml [tool.drifter]
4. Command-line overrides
"""

from __future__ import annotations

import fnmatch
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from drifter._toml_utils import safe_load_toml


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
        {"name": "doc_coverage", "enabled": True, "severity": "warn"},
        {"name": "pre_flight_sync", "enabled": True, "severity": "warn"},
        {"name": "credential_leak", "enabled": True, "severity": "error"},
        {"name": "dead_code", "enabled": True, "severity": "warn"},
        {"name": "test_coverage", "enabled": True, "severity": "warn"},
        {"name": "cli_output", "enabled": True, "severity": "warn"},
        {"name": "gitignore", "enabled": True, "severity": "error"},
        {"name": "pipeline_integrity", "enabled": True, "severity": "error"},
        {"name": "archive_integrity", "enabled": True, "severity": "error"},
        {"name": "tomllib_compatibility", "enabled": True, "severity": "error"},
        {"name": "audit_coverage", "enabled": True, "severity": "error"},
        {"name": "reporter_completeness", "enabled": True, "severity": "error"},
        {"name": "agent_self_audit", "enabled": True, "severity": "error"},
        {"name": "git_commit_approval", "enabled": True, "severity": "error"},
        {"name": "tree_integrity", "enabled": True, "severity": "error"},
        {"name": "file_size", "enabled": True, "severity": "error"},
        {"name": "manifest_sync", "enabled": True, "severity": "error"},
        {"name": "claim_sync", "enabled": True, "severity": "error"},
        {"name": "read_before_write", "enabled": True, "severity": "error"},
        {"name": "test_after_write", "enabled": True, "severity": "error"},
        {"name": "drift_check_after_write", "enabled": True, "severity": "error"},
        {"name": "no_rush", "enabled": True, "severity": "error"},
        {"name": "config_sync", "enabled": True, "severity": "error"},
        {"name": "ghost_reference", "enabled": True, "severity": "warn"},
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
    severity: str = "warn"  # ceiling: this check's issues report at no higher severity
    ignore_paths: list[str] = field(default_factory=list)
    ignore_patterns: list[str] = field(default_factory=list)
    path: str | None = None  # custom check: Python file to load the check from


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
    def load(
        cls, root: Path | None = None, overrides: dict[str, Any] | None = None
    ) -> Config:
        """Load configuration from defaults, files, and overrides."""
        raw = dict(DEFAULT_CONFIG)

        resolved_root = root or Path(".")
        resolved_root = resolved_root.resolve()

        # Try drifter.toml
        drifter_toml = resolved_root / "drifter.toml"
        if drifter_toml.exists():
            drifter_data = _load_toml(drifter_toml)
            # Support [drifter], legacy [tool.drifter], and root-level keys
            if "drifter" in drifter_data:
                raw = _merge(raw, drifter_data["drifter"])
            elif "tool" in drifter_data and "drifter" in drifter_data["tool"]:
                raw = _merge(raw, drifter_data["tool"]["drifter"])
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
        check_configs: dict[str, dict[str, Any]] = {
            c["name"]: c for c in raw.get("checks", [])
        }
        # Apply per-check overrides from [drifter.check_config.<name>].
        # Unknown names are kept (not dropped) so run_checks can warn about
        # them or load them as custom checks when they declare a path.
        for name, patch in raw.get("check_config", {}).items():
            if name in check_configs:
                check_configs[name] = _merge(check_configs[name], patch)
            else:
                check_configs[name] = {"name": name, **patch}

        checks = [
            CheckConfig(
                name=name,
                enabled=c.get("enabled", True),
                severity=c.get("severity", "warn"),
                ignore_paths=c.get("ignore_paths", []),
                ignore_patterns=c.get("ignore_patterns", []),
                path=c.get("path"),
            )
            for name, c in check_configs.items()
        ]

        return cls(
            root=resolved_root,
            max_pending_age_days=raw.get("max_pending_age_days", 7),
            drift_threshold=raw.get("drift_threshold", 70),
            history_path=raw.get("history_path"),
            checks=checks,
            ignore=IgnoreConfig(paths=raw.get("ignore", {}).get("paths", [])),
        )

    def check_config(self, name: str) -> CheckConfig:
        """Return configuration for a specific check, or a default."""
        for c in self.checks:
            if c.name == name:
                return c
        return CheckConfig(name=name)

    def is_ignored(self, path: Path) -> bool:
        """Check if a path matches any ignore pattern."""
        str_path = str(path)
        for pattern in self.ignore.paths:
            if fnmatch.fnmatch(str_path, pattern):
                return True
            if pattern.endswith("/"):
                # Directory pattern: match its segments as a contiguous
                # subsequence of the path's parts (works for relative and
                # absolute paths, single- and multi-segment patterns).
                dir_parts = Path(pattern).parts
                parts = path.parts
                n = len(dir_parts)
                if n and any(
                    tuple(parts[i : i + n]) == dir_parts
                    for i in range(len(parts) - n + 1)
                ):
                    return True
            elif fnmatch.fnmatch(path.name, pattern):
                return True
        return False

    def is_check_ignored(self, check_name: str, path: Path) -> bool:
        """Check if a path is ignored for a specific check."""
        cfg = self.check_config(check_name)
        str_path = str(path)
        try:
            rel_path = str(path.relative_to(self.root))
        except ValueError:
            rel_path = str_path
        for pattern in cfg.ignore_paths + cfg.ignore_patterns:
            if fnmatch.fnmatch(str_path, pattern):
                return True
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            if fnmatch.fnmatch(path.name, pattern):
                return True
        return self.is_ignored(path)


def _load_toml(path: Path) -> dict[str, Any]:
    result = safe_load_toml(path)
    if result is None:
        warnings.warn(
            f"Could not parse {path} — file is corrupted or unreadable; "
            "its settings are ignored",
            stacklevel=3,
        )
        return {}
    return result


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge override into base.

    Dicts merge recursively. Lists of dicts that all carry a ``name`` key
    (e.g. ``checks``) merge per entry: an override entry updates the base
    entry with the same name, preserving base fields the override omits, and
    new names are appended. All other values replace wholesale. An explicit
    empty list still replaces, so ``checks = []`` disables the suite.
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge(result[key], value)
        elif (
            key in result
            and value
            and _is_named_dict_list(result[key])
            and _is_named_dict_list(value)
        ):
            result[key] = _merge_named_list(result[key], value)
        else:
            result[key] = value
    return result


def _is_named_dict_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, dict) and "name" in item for item in value
    )


def _merge_named_list(
    base: list[dict[str, Any]], override: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    merged = [dict(item) for item in base]
    index = {item["name"]: i for i, item in enumerate(merged)}
    for item in override:
        name = item["name"]
        if name in index:
            merged[index[name]] = _merge(merged[index[name]], item)
        else:
            index[name] = len(merged)
            merged.append(dict(item))
    return merged

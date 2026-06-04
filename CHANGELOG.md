# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-06-04

### Added

- **Anti-Hallucination Stack**
  - `src/drifter/manifest_generator.py` — scans codebase and emits `.drifter/capability-manifest.json`
  - `drifter manifest` CLI command — regenerates capability manifest on demand
  - `drifter describe --format json|markdown` — machine-readable project description for LLM consumption
  - `GhostReferenceCheck` — detects hallucinated `drifter <command>` and MCP tool references in markdown docs
  - Self-registering `@mcp_tool` decorator in MCP server with `get_registered_tools()` registry
- **Per-check suppression infrastructure** — `ignore_paths` and `ignore_patterns` for every built-in check
- **Cooperative Enforcement Model** documentation in README

### Security

- Replaced subprocess `grep` in pre-flight with native Python scan (command injection fix)
- HMAC-SHA256 tamper detection for session audit logs
- `safe_load_toml()` wrapper for safe TOML parsing
- GitCommitApprovalCheck strengthened to last-5-commits with destructive-keyword regex
- 10s timeout on shell history reading
- Optional `DRIFTER_MCP_TOKEN` auth for MCP tools
- Expanded credential leak patterns (URLs, PEM, AWS, high-entropy tokens)

### Changed

- 35 built-in checks (was 34)
- Capped drift score formula with health indicator (`clean` / `degraded`)
- All check modules migrated to `safe_load_toml()`
- File size limits adjusted for legitimate growth

### Fixed

- Template drift: `AGENTS.md` type consistency, command alignment
- `ArchitectureDocSyncCheck` multiline regex
- Python 3.10 compatibility (`tomli` fallback)
- 48 ruff lint errors, 4 mypy errors

## [0.2.0] — 2026-05-27

### Added

- `drifter-manifest.toml` — canonical manifest for tree structure, check counts, file limits
- `ManifestSyncCheck`, `TreeIntegrityCheck`, `FileSizeCheck`, `ClaimSyncCheck`
- Session audit logger with per-project append-only logs
- `AgentSelfAuditCheck` and `GitCommitApprovalCheck` behavioral checks
- `HistoryReader` — cross-platform shell history (bash, zsh, fish)
- `ToolInterceptor` for plugin integrations
- MCP server skeleton in `plugins/mcp-server/`
- Git pre-commit hook (`install-hook` / `uninstall-hook`)
- 34 built-in drift checks
- 3 reporters: console, JSON, GitHub Actions

## [0.1.0] — 2026-05-20

### Added

- Initial release
- Core drift guard engine (`drift_guard.py`)
- Pre-flight checklist (`pre_flight.py`)
- Project conductor (`conductor.py`)
- Document validator with type system (`doc_validator.py`)
- Shell guard with dangerous patterns enforcement (`shell_guard.py`)
- `drifter check`, `drifter preflight`, `drifter validate`, `drifter conductor` CLI commands

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] — 2026-10-07

### Security

- **Shell guard no longer fails open on compound commands** — commands are split
  on `&&`, `||`, `;`, `|` (quote-aware), every segment is classified, and the
  strictest verdict wins. Previously `git status && rm -rf ~` (and similar
  smuggling behind any allow-listed command) classified as `allow`.
- **Pipe-to-shell blocks match real-world invocations** — `curl -fsSL URL | sh`
  and `wget -qO- URL | bash` now hit the `curl | sh` / `wget | sh` family of
  blocked patterns (previously only the literal flagless strings matched).
- **Enforcement fails closed on a broken patterns file** — a missing, corrupt,
  or rule-less `dangerous_patterns.toml` now blocks all commands with a clear
  reason instead of silently allowing everything.
- **Git block-list gaps closed** — `git switch -c`, `git checkout .`, and
  `git restore .` added to `always_block`.
- **`Classification` moved to `drifter._types`** — eliminates the circular
  import between `shell_guard` and `errors` (and the lazy-import workaround).

### Added

- **Custom check loading** — `[[drifter.checks]]` / `[drifter.check_config.*]`
  entries with a `path` load a user check class (a `run(root, config)` contract)
  via importlib. Missing file / import error / wrong class count produce an
  error-level issue; unknown names without a `path` produce a typo-guard warning
  instead of silent skipping. Severity ceiling applies to custom checks exactly
  as for builtins. Documented in `docs/architecture.md` (the section previously
  described a mechanism that did not exist).
- **`drifter log-rotate` command** — archives the session log and starts fresh
  (the upgrade path for projects whose legacy logs trip current behavioral checks).
- **`mcp` optional extra** — `pip install "drifter-check[mcp]"` installs `fastmcp` for the
  MCP server plugin.
- **`DRIFTER_ROOT` env var** in the MCP server — default root when a tool call
  passes none (per-call `root` wins; cwd is the fallback).
- **Apache-2.0 license classifier** (license was already `MIT OR Apache-2.0`).
- **Pinned tool configs** — `[tool.ruff]` (py310) and `[tool.mypy]` (py310, with a
  `tomli` missing-imports override) in `pyproject.toml`.
- **Preflight records drift score** — `drifter preflight` now appends to the
  conductor's Drift Score History. `drifter check` remains side-effect-free.
- **`drifter preflight --task` is wired** — the task description appears in the
  report header and is logged to the session audit log.
- **PyPI publish workflow** (`.github/workflows/publish.yml`) — tag-triggered
  build + trusted publishing.
- **Shared test fixtures** (`tests/conftest.py`) — `git_repo`, `fake_project`,
  `minimal_project`, `pre_flight_project`; plus CLI dispatch tests (every
  subcommand's routing is verified) and `tests/test_checks_sync.py` /
  `tests/test_checks_code_quality.py` (previously-untested modules).

### Changed

- **PyPI distribution renamed to `drifter-check`** — `pip install drifter`
  installed an unrelated 2015 package. The CLI command stays `drifter`.
  License metadata modernized to the PEP 639 SPDX string form.
- **Templates moved into the package** — from repo-root `templates/` to
  `src/drifter/templates/`, shipped as wheel package data and resolved via
  `importlib.resources` (`drifter._templates`).
- **Reporters are the single output path** — `cmd_check` delegates to
  `ConsoleReporter`/`JsonReporter`/`GitHubActionsReporter`; the inline formatters
  are deleted. `reporter_completeness` now verifies `src/drifter/reporters/console.py`.
- **JSON output schema upgraded** — `drifter check --json` now emits structured
  issue objects (`[{check, file, detail, severity}]`) inside the metadata envelope
  instead of `repr()` strings (which were not machine-parseable).
- **`--format {console,json,github}`** replaces the overlapping `--json` flag
  (kept as a deprecated alias).
- **`cli.py` split** — parser + dispatch remain in `cli.py`; command handlers
  live in `_cli_check.py`, `_cli_conductor.py`, `_cli_init.py`, `_cli_admin.py`.
- **Check accuracy** — `digest_staleness` inspects list items only (no more
  prose false positives) and skips archive-designated docs; `test_coverage` uses
  exact stem conventions (substring matching made `sync.py` falsely "covered");
  conductor tables parse by header name (both layouts); `ghost_reference`
  dedupes, carries line numbers, and skips `docs/archive` + draft docs;
  behavioral checks share one cached log parse and match real command words;
  the agent-behavior history timeout genuinely bounds runtime now.
- **Manifest generation is AST-based** (was regex on source) and warns on
  zero-yield degradation.
- **`drifter-manifest.toml` pruned to live policy** — dead `[boundaries]`,
  `[generated]`, `[pre_flight]`, and unused `[structure]` keys removed; file
  budgets re-baselined to a documented ~15% headroom policy.
- `docs/wiki.md` v1.3, and a full documentation sweep: conductor rewritten to
  truthful state, missing session digests backfilled, every command name /
  severity / code snippet verified against the code.

### Fixed

- **`drifter init` works from installed wheels** — a genuinely missing template
  is a hard error instead of a placeholder stub (previously `init` silently
  wrote an empty `dangerous_patterns.toml` and "Template not found" stubs).
- **`drifter init --full` is real** — the four optional doc stubs are only
  written with `--full`.
- **`python -m drifter` propagates exit codes** — `__main__` now uses
  `sys.exit(main())`; previously the module form always exited 0 (CI using the
  module form silently passed on drift).
- **MCP tools ship with descriptions again** — all five tool docstrings were
  dead string expressions placed after the auth checks, so FastMCP and the
  capability manifest emitted empty descriptions.
- **Archive records no longer fabricate `score: 100`** — the real drift score
  is recorded, or the field is omitted.
- **Corrupt `drifter.toml` / `pyproject.toml` surfaces a warning** instead of
  silently running on built-in defaults.
- **Config merge semantics** — `[[drifter.checks]]` entries merge per `name`
  into `DEFAULT_CONFIG` instead of replacing the whole check list. An explicit
  `checks = []` still disables the suite.
- **Legacy `[tool.drifter]` section in `drifter.toml` is honored again.**
- **Extension-named directories no longer crash checks** — a directory like
  `whisper.android.java` raised `IsADirectoryError` in `credential_leak`,
  `git_safety`, and `hardcoded_path`.
- **Multi-segment ignore patterns work on relative paths** — `is_ignored()`
  matches directory patterns as path-part subsequences.
- **`tree_integrity` skips tool caches and build artifacts** — `.mypy_cache`,
  `.ruff_cache`, `.coverage`, `dist/`.
- **Per-check `severity` config is now applied** — ceiling semantics (demote,
  never escalate). Default severities curated to each check's maximum emitted
  severity (`pipeline_integrity`, `tree_integrity`, `file_size`, `claim_sync`,
  `no_rush` corrected from `warn` to `error`).
- **README truthfulness** — check-registry severities regenerated from
  `drifter describe`; the `enforce("sudo ...")` example corrected (it warns,
  not raises); install instructions use `drifter-check`.
- **Session heuristics** — test runs require a word-boundary `pytest` match;
  CHECK-action log entries always count as drift checks.
- **`CHANGELOG.md` at repo root is exempt from doc validation.**

### Removed

- Dead code (deletions reference-verified): `Task` dataclass,
  `_RE_DRIFTER_CMD_LOOSE`, empty `sys.version_info` guard blocks, `Report.health`
  (never consumed), `ToolInterceptor.config` (never read), the MCP server's
  unused `_MCP_REGISTRY`/`get_registered_tools()`, argparse-redundant defensive
  branches, and the duplicated conductor table-insert / manifest-loader /
  banner blocks (now single helpers).
- Tautological tests (`callable()` smoke tests, `rc in (0, 1)`, no-assertion
  crash tests) — replaced with behavioral assertions.
- (`CheckConfig.path`, removed earlier in the 0.4.0 cycle as dead, was
  reintroduced and wired for real — see custom check loading above.)

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

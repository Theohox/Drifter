# Drifter — Universal AI Agent Drift Guard

> **Before you write a single line of code, know what already exists.**

AI coding agents excel at local optimization and fail at project discipline over long horizons. Drifter is a lightweight governance layer — not a prompt, not a replacement — that keeps agents aligned with project structure as codebases evolve.

- **Document type system** — every doc knows its mutation rules; docs don't become lies
- **Project conductor** — one active task at a time; scope creep is structurally prevented
- **35 automated drift checks** — stale refs, doc drift, credential leaks, dead code, file-size bloat, ghost references, and more
- **Pre-flight checklist** — 7 designed-to-be-followed steps before any code change
- **Command boundaries** — agents read `dangerous_patterns.toml` before running shell
- **Real enforcement** — `ShellGuard.enforce()` raises `DangerousCommandError` or `ApprovalRequiredError` on violation
- **Plugin API** — `ToolInterceptor` auto-logs and enforces before any tool call (MCP, Kimi, custom)
- **Cross-platform shell history** — audit bash, zsh, and fish history with auto-detection
- **Git pre-commit hook** — block commits that introduce drift (`drifter install-hook`)
- **Session audit** — HMAC-signed tamper-evident log of reads, writes, and checks; forged entries are detected and skipped
- **Granular suppression** — per-check `ignore_paths` and `ignore_patterns` via `drifter.toml`

Drifter is a cooperative guard — it raises the cost of mistakes and makes them auditable, not impossible. For mandatory enforcement, pair it with git pre-commit hooks and CI gates.

Drifter is not a prompt. It is a **system of enforced protocols**.

## Quick Start

Requires **Python 3.10+**.

```bash
# Install
pip install drifter

# Initialize in your project
cd your-project
drifter init

# Run the drift guard
drifter check

# Run pre-flight before a coding session
drifter preflight --task "fix login bug"
```

## What You Get

| Artifact | Purpose |
|----------|---------|
| `AGENTS.md` (repo root) | Canonical agent contract. Read first, every session. |
| `dangerous_patterns.toml` | Command boundaries. Agents read this before running shell. |
| `docs/session-protocol.md` | Hard rules: scope, evidence, no-recreation, stop rule. |
| `docs/project-conductor.md` | Single source of truth: what's active, blocked, done. |
| `docs/archive/README.md` | Completed task records. One file per finished task. |
| `drifter check` | 35 automated checks: stale refs, hardcoded paths, doc drift, credential leaks, dead code, ghost references, and more. |
| `drifter preflight` | Enforced 7-step pre-flight before any code change. |
| `drifter conductor` | CLI for managing active tasks and phase state. |
| `drifter validate` | Validate document types and frontmatter. |
| `drifter audit` | Audit session history for dangerous command violations. |
| `drifter log` | Log agent actions (READ/WRITE/SHELL/CHECK) to per-project session audit. |
| `drifter session-report` | Generate behavioral report card from session audit log. |
| `drifter init` | Initialize Drifter in a new project. |
| `drifter install-hook` | Install git pre-commit hook that blocks commits with drift. |
| `drifter uninstall-hook` | Remove the Drifter pre-commit hook. |

<!-- Generated from `drifter describe --format markdown` — regenerate when checks change -->
<details>
<summary>Full check registry (35 checks)</summary>

| Check | Description | Severity |
|-------|-------------|----------|
| `stale_reference` | Scan markdown files for file/path references and verify they exist. | warn |
| `hardcoded_path` | Scan source files for hardcoded paths and verify they exist. | error |
| `digest_staleness` | Check digests for PENDING/TODO items older than threshold. | warn |
| `conductor_health` | Verify the Conductor file has exactly one active task and valid phase. | error |
| `cross_doc_consistency` | Check for cross-document inconsistencies (e.g., stale references between docs). | warn |
| `git_safety` | Scan source files for git mutation commands in shell calls or subprocess. | error |
| `dangerous_patterns` | Verify dangerous_patterns.toml exists and is referenced in AGENTS.md. | error |
| `timestamp_staleness` | Check that markdown frontmatter 'updated:' timestamps reflect actual file modification time. | warn |
| `conductor_content` | Verify conductor contains current data (non-empty evidence, score history). | warn |
| `architecture_doc_sync` | Verify architecture.md reflects current number of checks and CLI commands. | warn |
| `readme_completeness` | Verify README.md mentions all canonical artifacts and CLI commands. | warn |
| `doc_coverage` | Verify AGENTS.md documents all modules, CLI commands, and features. | warn |
| `pre_flight_sync` | Verify pre_flight.py and session-protocol.md agree on step count and dangerous_patterns. | warn |
| `credential_leak` | Scan source files for hardcoded credentials and secrets. | error |
| `dead_code` | Flag Python modules with zero imports from the rest of the codebase. | warn |
| `test_coverage` | Verify every source module has a corresponding test file. | warn |
| `cli_output` | Verify CLI output (especially init) mentions all canonical files. | warn |
| `gitignore` | Verify sensitive file patterns from dangerous_patterns.toml are in .gitignore if files exist. | error |
| `pipeline_integrity` | Verify conductor task references are consistent and tasks don't exist in multiple states. | warn |
| `archive_integrity` | Verify archive files have valid frontmatter and consistent naming. | error |
| `tomllib_compatibility` | Scan for bare 'import tomllib' without Python 3.11 version guard. | error |
| `audit_coverage` | Verify cmd_audit handles all ShellGuard action types. | error |
| `reporter_completeness` | Verify console reporter handles all severity levels explicitly. | error |
| `agent_self_audit` | Scan agent shell history for dangerous commands. | error |
| `git_commit_approval` | Verify recent commits have approval markers. | error |
| `tree_integrity` | Verify every file on disk is declared in drifter-manifest.toml and every declared file exists. | warn |
| `file_size` | Verify no module exceeds manifest-declared max_file_lines. | warn |
| `manifest_sync` | Verify BUILTIN_CHECKS count matches manifest-declared count. | error |
| `claim_sync` | Verify numerical claims in docs match manifest values. | warn |
| `read_before_write` | Verify every WRITE has a preceding READ on the same file. | error |
| `test_after_write` | Verify a test run happened after the most recent WRITE. | error |
| `drift_check_after_write` | Verify drifter check was run after the most recent WRITE. | error |
| `no_rush` | Verify at least one drift check per 3 WRITEs. | warn |
| `config_sync` | Verify config.py DEFAULT_CONFIG and drifter.toml match manifest checks. | error |
| `ghost_reference` | Scan markdown docs for references to non-existent commands or MCP tools. | warn |

</details>

## The 7-Step Pre-Flight

Every session starts with this exact sequence:

1. **READ** `AGENTS.md` — the agent contract
2. **READ** `docs/session-protocol.md` — hard rules
3. **READ** `docs/project-conductor.md` — what's active?
4. **RUN** `drifter check` — what's the current drift?
5. **PICK** one active task from the conductor
6. **GREP** for existing code before writing new code
7. **READ** `dangerous_patterns.toml` — command boundaries before running shell

Designed to be followed every session.

## Cost

Drifter costs ~9,000 input tokens per session (the pre-flight docs). That's ~4.5% of a 200K context window.

## Philosophy

Reactive prompting fails because agents ignore long prompts under pressure. Proactive enforcement works because **scripts + structure > words**.

Drifter treats documentation as a correctness layer, not an afterthought. Every document has a **type** with mutation rules:

| Type | Example | Rule |
|------|---------|------|
| **Constitution** | `AGENTS.md` | Stable principles. Rarely changes. |
| **Snapshot** | `docs/digests/index.md` | Current truth only. Rewrite, don't append. |
| **Backlog** | `docs/project-conductor.md` | Open work only. Remove items when done. |
| **Archive** | `docs/archive/` | One file per completed task. Auto-generated on `mark_done()`. |
| **Playbook** | `docs/session-protocol.md` | Operational procedures. Update when process changes. |
| **Index** | `docs/phase-index.md` | Maps all docs to their phase without moving files. |

When every doc knows its type, docs don't become lies.

## How Drifter Compares

| Approach | Memory | Discipline | Drift Detection | Scope Control | Cross-Session |
|----------|--------|-----------|-----------------|---------------|---------------|
| `.cursorrules` | ❌ | ❌ | ❌ | ❌ | ❌ |
| Claude-Mem | ✅ | ❌ | ❌ | ❌ | ✅ |
| Built-in Planning | ❌ | ⚠️ Weak | ❌ | ❌ | ❌ |
| Traditional Linting | ❌ | ❌ | ❌ | ❌ | ❌ |
| Code Review | ❌ | ⚠️ Reactive | ⚠️ Manual | ⚠️ Manual | ❌ |
| **Drifter** | ❌* | ✅ | ✅ | ✅ | ✅** |

\* Drifter does not provide memory. Pair with Claude-Mem or digests for memory.  
\** Drifter provides cross-session persistence via conductor and digests, but not automatic context injection.

**Verdicts:**
- **vs `.cursorrules`** — `.cursorrules` is a prompt. Drifter is a system. Use both: style in `.cursorrules`, structure in Drifter.
- **vs Claude-Mem** — Claude-Mem remembers what happened. Drifter prevents mistakes from happening. Use both.
- **vs Built-in Planning** — Agent planning is tactical execution. The conductor is strategic control of what tasks exist.
- **vs Linting** — Linters catch code issues. Drifter catches documentation and process drift. Complementary.
- **vs Code Review** — Review catches the 20% that needs human judgment. Drifter catches common patterns: stale refs, undocumented changes, scope creep.

## Evidence

The problem Drifter solves is not hypothetical:

- **Apiiro (Sep 2025)**: AI-generated code introduced >10,000 new security findings/month by June 2025 — a 10x increase from Dec 2024
- **DORA 2025**: Higher AI adoption correlates with increased software delivery instability; 30% of developers report little/no trust in AI-generated code
- **Packmind / ContextOps**: Documented "context decay" — conventions shift, libraries break, standards degrade without active countermeasures
- **Industry consensus**: `.cursorrules` and `CLAUDE.md` are static artifacts with "no lifecycle management, no versioning, no modification history, no drift detection"

No other tool combines pre-flight enforcement, drift detection, document type constraints, scope control, command boundaries, and session audit in a single `pip install`.

## Enforcement Layer

Drifter is not just a linter — it can actively block dangerous commands:

```python
from drifter.shell_guard import ShellGuard

guard = ShellGuard()
guard.enforce("git commit -m 'fix'")  # Raises DangerousCommandError
guard.enforce("sudo apt install x")   # Raises ApprovalRequiredError
guard.enforce("git status")           # Returns Classification(action="allow")
```

For plugin authors, `ToolInterceptor` auto-logs and enforces before every tool call:

```python
from drifter.plugin_api import ToolInterceptor

interceptor = ToolInterceptor()
interceptor.before_read("src/main.py")      # Logs READ
interceptor.before_write("src/main.py")     # Logs WRITE
interceptor.before_shell("git status")      # Logs SHELL + enforces
```

## Cooperative Enforcement Model

Drifter constrains well-behaved agents through protocols and structure. It is **not** a mandatory gate that a determined agent cannot bypass. For enforcement that agents cannot ignore, pair Drifter with:

- **Git pre-commit hooks** (`drifter install-hook`) — blocks commits with drift at the git layer
- **CI/CD integration** — run `drifter check` in GitHub Actions; fail the build on errors
- **Required approval markers** — `GitCommitApprovalCheck` verifies destructive commits have `[APPROVED BY ...]` markers

Drifter is most effective when the agent is cooperative and the human reviews session reports regularly. For high-risk environments, combine with mandatory CI gates.

## MCP Server Plugin

An MCP server is available in `plugins/mcp-server/`:

```bash
cd plugins/mcp-server
pip install fastmcp
python server.py
```

Exposes Drifter tools as MCP tools:
- `drifter_classify` — classify a command without enforcing
- `drifter_enforce` — enforce a command (blocked/approval_required/allowed)
- `drifter_log` — log an action to the session audit
- `drifter_preflight` — run the 7-step pre-flight checklist
- `drifter_check` — run the full drift guard

Optional token authentication via `DRIFTER_MCP_TOKEN` environment variable.

## Documentation

- [`docs/methodology.md`](docs/methodology.md) — The "why" in detail
- [`docs/adoption-guide.md`](docs/adoption-guide.md) — Step-by-step for any project
- [`docs/rules-reference.md`](docs/rules-reference.md) — Complete rule catalog

## Development

```bash
# Clone and install in editable mode with dev dependencies
git clone https://github.com/Theohox/Drifter.git
cd Drifter
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -q

# Run drift guard on itself
drifter check

# Or run from source without installing
python -m drifter check

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or https://www.apache.org/licenses/LICENSE-2.0)
- MIT license ([LICENSE-MIT](LICENSE-MIT) or https://opensource.org/licenses/MIT)

at your option.

## Contribution

Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in the work by you, as defined in the Apache-2.0 license, shall be dual licensed as above, without any additional terms or conditions.

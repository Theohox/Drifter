# Drifter — Universal AI Agent Drift Guard

> **Before you write a single line of code, know what already exists.**

AI coding agents generate code faster than teams can review it. The result is predictable: hallucinated files, undocumented bloat, context blindness, and docs that become lies. Apiiro found AI-generated code introduced **>10,000 new security findings per month** by mid-2025 — a 10x increase. The DORA report found that **30% of developers don't trust AI-generated code**.

Drifter is a `pip install` defense layer. It does not replace your agent. It constrains it.

- **Pre-flight checklist** — 7 enforced steps before any code change
- **34 automated drift checks** — stale refs, doc drift, credential leaks, dead code, file-size bloat, and more
- **Document type system** — every doc knows its mutation rules; docs don't become lies
- **Project conductor** — one active task at a time; scope creep is structurally prevented
- **Command boundaries** — agents read `dangerous_patterns.toml` before running shell
- **Real enforcement** — `ShellGuard.enforce()` raises `DangerousCommandError` or `ApprovalRequiredError` on violation
- **Plugin API** — `ToolInterceptor` auto-logs and enforces before any tool call (MCP, Kimi, custom)
- **Cross-platform shell history** — audit bash, zsh, and fish history with auto-detection
- **Git pre-commit hook** — block commits that introduce drift (`drifter install-hook`)
- **Session audit** — HMAC-signed tamper-evident log of reads, writes, and checks; forged entries are detected and skipped
- **Granular suppression** — per-check `ignore_paths` and `ignore_patterns` via `drifter.toml`

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
| `drifter check` | 34 automated checks: stale refs, hardcoded paths, doc drift, credential leaks, dead code, and more. |
| `drifter preflight` | Enforced 7-step pre-flight before any code change. |
| `drifter conductor` | CLI for managing active tasks and phase state. |
| `drifter validate` | Validate document types and frontmatter. |
| `drifter audit` | Audit session history for dangerous command violations. |
| `drifter log` | Log agent actions (READ/WRITE/SHELL/CHECK) to per-project session audit. |
| `drifter session-report` | Generate behavioral report card from session audit log. |
| `drifter init` | Initialize Drifter in a new project. |
| `drifter install-hook` | Install git pre-commit hook that blocks commits with drift. |
| `drifter uninstall-hook` | Remove the Drifter pre-commit hook. |

## The 7-Step Pre-Flight

Every session starts with this exact sequence:

1. **READ** `AGENTS.md` — the agent contract
2. **READ** `docs/session-protocol.md` — hard rules
3. **READ** `docs/project-conductor.md` — what's active?
4. **RUN** `drifter check` — what's the current drift?
5. **PICK** one active task from the conductor
6. **GREP** for existing code before writing new code
7. **READ** `dangerous_patterns.toml` — command boundaries before running shell

No exceptions. No "I'll just quickly fix this one thing."

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
- **vs Code Review** — Review catches the 20% that needs human judgment. Drifter catches the 80% of routine mistakes automatically.

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

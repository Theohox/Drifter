---
title: Drifter Internal Architecture
type: snapshot
status: active
phase: 0
created: '2026-05-27T00:00:00Z'
updated: '2026-10-07T12:42:00Z'
---

# Drifter Internal Architecture

How Drifter is built. For contributors and advanced users.

---

## Design Principles

1. **Zero-dependency core** — Basic drift detection works with only the Python standard library
2. **Plugin architecture** — Checks and reporters are swappable
3. **Config in repo** — `drifter.toml` (`[drifter]` section) or `pyproject.toml [tool.drifter]`
4. **Fast feedback** — the `check` command runs in < 5 seconds on a 10k-file repo
5. **Language-agnostic** — Works with any project that has files and docs

CLI surface (13 commands): `drifter check`, `drifter preflight`, `drifter conductor`, `drifter validate`, `drifter audit`, `drifter init`, `drifter log`, `drifter log-rotate`, `drifter session-report`, `drifter install-hook`, `drifter uninstall-hook`, `drifter manifest`, `drifter describe`.

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                CLI (cli.py + _cli_* modules)                │
│         check │ preflight │ conductor │ admin commands      │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           Core Engine (drift_guard.py)                      │
│     check registry (BUILTIN_CHECKS) → parallel runner       │
│     → severity ceiling → Report                             │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│   Built-in Checks (35 in checks/) + custom checks (path)    │
│   Full registry: drifter describe or README.md              │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│   Reporters (reporters/)                                    │
│   ConsoleReporter · JsonReporter · GitHubActionsReporter    │
└─────────────────────────────────────────────────────────────┘

Config (config.py) feeds every layer:
defaults → drifter.toml → pyproject.toml [tool.drifter] → CLI flags

Optional modules: pre_flight.py, conductor.py, doc_validator.py,
shell_guard.py, session_logger.py, history_reader.py, plugin_api.py,
manifest_generator.py. Cross-session persistence: digests + conductor.
```

### Support Modules

Internal (underscore-prefixed) modules that the diagram elides:

| Module | Role |
|---|---|
| `src/drifter/_types.py` | Shared `Classification` / `ClassificationAction` — imported by both `shell_guard` and `errors` to avoid a circular import |
| `src/drifter/_templates.py` | Bundled template resolution via `importlib.resources` (`template_text`), with a repo-root `templates/` fallback for source checkouts |
| `src/drifter/_cli_common.py` | Shared CLI helpers (`print_banner`) |
| `src/drifter/_cli_check.py`, `_cli_conductor.py`, `_cli_init.py`, `_cli_admin.py` | CLI command handlers, split from `cli.py` (following the `_hook_commands.py` precedent) |
| `src/drifter/checks/_shared.py` | Shared check helpers — `load_drifter_manifest`, `PATH_SKIP_PATTERNS`, `is_skippable_path`, `resolve_doc_path`, `archive_designated_docs` |
| `src/drifter/checks/_base.py` | `Issue` (frozen dataclass) and the `Check` protocol |

---

## Check Protocol

A check is any class implementing the `Check` protocol from `src/drifter/checks/_base.py`:

```python
@dataclass(frozen=True)
class Issue:
    check: str
    file: str
    detail: str
    severity: str = "warn"  # "error" | "warn" | "info"

class Check(Protocol):
    name: str
    def run(self, root: Path, config: Config) -> list[Issue]: ...
```

Built-in checks are registered in `BUILTIN_CHECKS` in `src/drifter/checks/__init__.py` and run in parallel (ThreadPoolExecutor, ≤4 workers). Custom checks load from a `path` via importlib — see Extension Points below.

---

## Reporter Protocol

Reporters are plain classes (no formal `Protocol`) in `src/drifter/reporters/`, each exposing a `name` and `report(issues, meta=None) -> str`. `meta` carries report metadata (score, counts, timestamp); printing is the caller's job.

Built-in reporters:
- `ConsoleReporter` — grouped plain-text terminal report (no color codes)
- `JsonReporter` — JSON metadata envelope with structured issue objects
- `GitHubActionsReporter` — `::error::` and `::warning::` annotations

---

## Performance Budgets

A check run completes in under 5s on 10k files; all other commands < 1-2s in typical repos. Strategies: checks run in parallel (`concurrent.futures`); file scanning uses `pathlib.Path.rglob` with early filtering; regexes compiled once; results cached within a single run.

---

## Extension Points

### Custom Checks

Create a Python file defining exactly one check class — a class with a
`run(root, config)` method returning a list of `Issue`s:

```python
# my_checks/no_console_log.py
from pathlib import Path
from drifter.checks._base import Issue

class NoConsoleLogCheck:
    name = "no_console_log"

    def run(self, root: Path, config) -> list[Issue]:
        return [
            Issue(check=self.name, file=str(f.relative_to(root)),
                  detail="console.log found", severity="warn")
            for f in root.rglob("*.js")
            if "console.log(" in f.read_text()
        ]
```

Register it in `drifter.toml` with a `path`:

```toml
[[drifter.checks]]
name = "no_console_log"
path = "my_checks/no_console_log.py"   # relative to project root (or absolute)
enabled = true
severity = "warn"                   # ceiling: issues report no higher than this
```

The contract, enforced by `run_checks` in `src/drifter/drift_guard.py`:

- The file must define **exactly one** class with a `run()` method; it is
  instantiated with no arguments. If the instance has no `name`, the
  configured check name is assigned.
- `severity` acts as a ceiling, exactly as for built-in checks.
- A missing file, an import error, or the wrong number of check classes
  produces an error-level issue instead of a crash or silence.
- A configured check name with no builtin and no `path` produces a
  warn-level issue (typo guard).
- If the name collides with a built-in check, the builtin wins and a
  warn-level issue is emitted.

### Custom Reporters

Similar to checks, implement the Reporter protocol.

---

*This document is a snapshot. Rewrite it when architecture changes.*

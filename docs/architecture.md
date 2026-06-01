---
title: Drifter Internal Architecture
type: snapshot
status: active
phase: 0
created: '2026-05-27T00:00:00Z'
updated: '2026-06-01T14:21:00Z'
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

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI (cli.py)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   check     │  │  preflight  │  │     conductor       │  │
│  │  command    │  │   command   │  │      command        │  │  command   │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│         ▼                ▼                     ▼             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Core Engine (drifter/drift_guard.py)       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │
│  │  │   Check     │  │   Check     │  │   Check     │   │   │
│  │  │  Registry   │  │   Runner    │  │  Pipeline   │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│         │                │                     │             │
│         ▼                ▼                     ▼             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Built-in Checks (34)                    │   │
│  │  • StaleReferenceCheck                               │   │
│  │  • HardcodedPathCheck                                │   │
│  │  • DigestStalenessCheck                              │   │
│  │  • ConductorHealthCheck                              │   │
│  │  • CrossDocConsistencyCheck                          │   │
│  │  • GitSafetyCheck                                    │   │
│  │  • DangerousPatternsCheck                            │   │
│  │  • TimestampStalenessCheck                           │   │
│  │  • ConductorContentCheck                             │   │
│  │  • ArchitectureDocSyncCheck                          │   │
│  │  • ReadmeCompletenessCheck                           │   │
│  │  • PreFlightSyncCheck                                │   │
│  │  • CredentialLeakCheck                               │   │
│  │  • DeadCodeCheck                                     │   │
│  │  • TestCoverageCheck                                 │   │
│  │  • CliOutputCheck                                    │   │
│  │  • GitignoreCheck                                    │   │
│  │  • PipelineIntegrityCheck                            │   │
│  │  • ArchiveIntegrityCheck                             │   │
│  │  • TomllibCompatibilityCheck                         │   │
│  │  • AuditCoverageCheck                                │   │
│  │  • ReporterCompletenessCheck                         │   │
│  │  • AgentSelfAuditCheck                               │   │
│  │  • GitCommitApprovalCheck                            │   │
│  │  • TreeIntegrityCheck                                │   │
│  │  • FileSizeCheck                                     │   │
│  │  • ManifestSyncCheck                                 │   │
│  │  • ClaimSyncCheck                                    │   │
│  │  • ReadBeforeWriteCheck                              │   │
│  │  • TestAfterWriteCheck                               │   │
│  │  • DriftCheckAfterWriteCheck                         │   │
│  │  • NoRushCheck                                       │   │
│  │  • ConfigSyncCheck                                   │   │
│  │  • DocCoverageCheck                                  │   │
│  └──────────────────────────────────────────────────────┘   │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Reporters                               │   │
│  │  • ConsoleReporter (human-readable)                  │   │
│  │  • JsonReporter (machine-parseable)                  │   │
│  │  • GitHubActionsReporter (CI annotations)            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              Config (config.py)                             │
│  Loads from: drifter.toml, pyproject.toml, or defaults      │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              Optional Modules                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  pre_flight │  │  conductor  │  │   doc_validator     │  │
│  │   runner    │  │   manager   │  │     checker         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Memory Layer (removed)                  │   │
│  │  Was `src/drifter/memory/`. Deleted as dead code.    │   │
│  │  Cross-session persistence via digests + conductor.  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Check Protocol

A check is any callable that implements this protocol:

```python
from pathlib import Path
from typing import Protocol, List, runtime_checkable

@runtime_checkable
class Check(Protocol):
    name: str
    
    def run(self, root: Path, config: dict) -> List[Issue]:
        ...

class Issue:
    def __init__(self, check: str, file: str, detail: str, severity: str = "warn"):
        self.check = check      # check name
        self.file = file        # relative path
        self.detail = detail    # human-readable description
        self.severity = severity  # "error" | "warn" | "info"
```

Checks are registered in `src/drifter/drift_guard.py` and run in parallel where possible.

---

## Reporter Protocol

A reporter formats and outputs issues:

```python
from typing import Protocol, List, runtime_checkable

@runtime_checkable
class Reporter(Protocol):
    name: str
    
    def report(self, issues: List[Issue]) -> str:
        ...
```

Built-in reporters:
- `ConsoleReporter` — colored terminal output
- `JsonReporter` — JSON for piping to other tools
- `GitHubActionsReporter` — `::error::` and `::warning::` annotations

---

## Config Resolution

Config is loaded in this priority order (later overrides earlier):

1. Built-in defaults (`src/drifter/config.py`)
2. `drifter.toml` in project root (`[drifter]` section)
3. `pyproject.toml [tool.drifter]`
4. Command-line flags

---

## Performance Budgets

| Operation | Target | Worst Case |
|-----------|--------|------------|
| `drifter check` | < 5s for 10k files | < 30s for 100k files |
| `drifter validate` | < 1s for 100 docs | < 5s for 1k docs |
| `drifter preflight` | < 10s total | < 30s if drift guard is slow |
| `drifter conductor` | < 1s | < 5s |
| `drifter audit` | < 2s | < 10s |
| `drifter init` | < 1s | < 2s |
| `drifter log` | < 10ms | < 100ms |
| `drifter session-report` | < 100ms | < 500ms |

Performance strategies:
- Checks run in parallel using `concurrent.futures`
- File scanning uses `pathlib.Path.rglob` with early filtering
- Regex patterns are compiled once
- Results are cached within a single run

---

## Extension Points

### Custom Checks

Create a Python file with a Check class:

```python
# my_project/checks/no_console_log.py
from drifter.drift_guard import Issue
from pathlib import Path
import re

class NoConsoleLogCheck:
    name = "no_console_log"
    
    def run(self, root: Path, config: dict):
        issues = []
        pattern = re.compile(r"console\.log\(")
        for js_file in root.rglob("*.js"):
            text = js_file.read_text()
            for match in pattern.finditer(text):
                issues.append(Issue(
                    check=self.name,
                    file=str(js_file.relative_to(root)),
                    detail=f"console.log at line {text[:match.start()].count(chr(10)) + 1}",
                    severity="warn"
                ))
        return issues
```

Register in `drifter.toml`:

```toml
[[drifter.checks]]
name = "no_console_log"
path = "my_project/checks/no_console_log.py"
enabled = true
severity = "warn"
```

### Custom Reporters

Similar to checks, implement the Reporter protocol.

---

*This document is a snapshot. Rewrite it when architecture changes.*

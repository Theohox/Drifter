---
title: Drifter Adoption Guide
type: guide
status: active
phase: 0
created: '2026-05-27T00:00:00Z'
updated: '2026-06-04T19:24:00Z'
---

# Drifter Adoption Guide

This guide walks you through adopting Drifter in any project. Estimated time: 15 minutes.

---

## Prerequisites

- Python 3.10+
- A project with some documentation (even just a README)
- Commitment to running the pre-flight protocol before agent sessions

---

## Step 1: Install Drifter

```bash
git clone https://github.com/Theohox/Drifter.git
cd Drifter
pip install -e ".[dev]"
```

---

## Step 2: Initialize Drifter in Your Project

```bash
cd /path/to/your-project
drifter init
```

This creates:
- `AGENTS.md` — agent contract (from template)
- `dangerous_patterns.toml` — command restrictions (from template)
- `docs/session-protocol.md` — hard rules (from template)
- `docs/project-conductor.md` — active task tracker (from template)
- `docs/archive/README.md` — archive convention (from template)
- `docs/digests/index.md` — digest directory (from template)
- `drifter.toml` — project configuration

---

## Step 3: Customize the Templates

### 3.1 Edit `dangerous_patterns.toml`

This is the **canonical enforcement spec**. It tells every agent what commands are forbidden.

Customize the patterns for your project:

```toml
[git]
always_block = [
    "git commit",
    "git push",
    # Add project-specific git commands to block
]

[shell]
blocked = [
    "rm -rf /",
    # Add project-specific shell patterns to block
]
```

**This file is as critical as AGENTS.md.** If it doesn't exist, agents have no command boundaries.

### 3.2 Edit `AGENTS.md`

Replace the template sections with your project's specifics:

- **The Golden Rule**: What should agents grep for? (e.g., "grep for `api_` functions before adding new endpoints")
- **Pre-Flight Checklist**: What docs are canonical for your project?
- **What Already Exists**: Map common needs to existing code locations
- **Architecture Boundaries**: What should agents never touch?

Keep it under 300 lines. Agents read this every session — if it's too long, they'll skip it.

### 3.2 Edit `docs/session-protocol.md`

Customize the hard rules:

- **Scope Boundary Rule**: What is your project's typical scope? (e.g., "frontend changes never touch backend auth")
- **Evidence Rule**: What does evidence look like for your stack? (screenshots for UI, test output for APIs, benchmarks for performance)
- **Stop Rule**: What tests must pass before stopping?

### 3.3 Edit `docs/project-conductor.md`

Set up your first phase and active task:

```markdown
## Current Phase

**Phase 0: Drifter Adoption** 🟢 ACTIVE

**Goal**: Adopt Drifter methodology and verify it works.

**Exit Criteria**:
- [ ] AGENTS.md customized
- [ ] Session protocol customized
- [ ] Conductor initialized
- [ ] Drift guard runs clean
- [ ] Team/agents trained on pre-flight

## Active Task

| Field | Value |
|-------|-------|
| **ID** | FEAT-001 |
| **Name** | Customize Drifter templates |
| **Status** | 🟡 IN PROGRESS |
| **Evidence** | — |
| **Next** | CHECK-001: Run first drift guard check |
```

---

## Step 4: Configure Drifter

Edit `drifter.toml` (or add `[tool.drifter]` to `pyproject.toml`):

```toml
[drifter]
root = "."
max_pending_age_days = 7
drift_threshold = 70

# Optional: enable agent self-audit by pointing to shell history
# When unset (default), AgentSelfAuditCheck is disabled
# history_path = "~/.bash_history"

# Which checks to run
[[drifter.checks]]
name = "stale_reference"
enabled = true
severity = "warn"

[[drifter.checks]]
name = "hardcoded_path"
enabled = true
severity = "error"

# Add custom ignore patterns
[drifter.ignore]
paths = [
    "venv/",
    "node_modules/",
    "__pycache__/",
    ".git/",
]
```

---

## Step 5: Run the First Check

```bash
drifter check
```

Expect warnings on the first run — the templates reference files that don't exist yet. Fix them or add them to the ignore list.

Run again until you're satisfied:

```bash
drifter check --score
# DRIFT: 0 issues | 0 errors | 0 warns | SCORE: 100%
```

---

## Step 6: Train Your Agents

### For Kimi CLI

Add to your `.kimi/config.toml`:

```toml
[session]
pre_command = "drifter preflight"
```

### For Claude Code

Add to your `.claude/CLAUDE.md`:

```markdown
Before every session:
1. Read AGENTS.md
2. Read docs/session-protocol.md
3. Read docs/project-conductor.md
4. Run `drifter check`
5. Pick the active task from the conductor
6. Grep for existing code before writing
```

### For Custom Agents

Ensure your agent:
1. Reads `AGENTS.md` before generating code
2. Reads the conductor to find the active task
3. Runs `drifter check` and reports the score
4. Declares scope before editing files
5. Provides evidence before declaring "done"
6. Updates the conductor after completing a task

---

## Token Overhead

Drifter adds ~8,500–9,000 input tokens per session (the pre-flight docs an agent must read). Here's the breakdown:

| Document | Characters | ≈ Tokens |
|----------|-----------|----------|
| `AGENTS.md` | 13,600 | ~3,400 |
| `docs/session-protocol.md` | 5,900 | ~1,480 |
| `docs/project-conductor.md` | 12,700 | ~3,180 |
| `dangerous_patterns.toml` | 2,450 | ~610 |
| `drifter check` output (clean) | 340 | ~85 |
| `drifter check` output (with drift) | 1,500–3,000 | ~375–750 |

**Context window impact:**
- Claude 3.5 Sonnet (200K): ~4.5%
- GPT-4o (128K): ~7%
- Smaller models (32K): ~28%

### The ROI

One prevented mistake pays for 1–3 sessions of Drifter overhead:

| Failure Mode | Typical Token Cost to Fix | Prevented By |
|-------------|--------------------------|--------------|
| Hallucinated file | 3K–8K | TreeIntegrityCheck, ManifestSyncCheck |
| Doc drift (docs lie) | 5K–15K | StaleReferenceCheck, CrossDocConsistencyCheck |
| Scope creep | 4K–10K | Conductor, Scope Boundary Rule |
| Undocumented command | 2K–5K | GhostReferenceCheck, CliOutputCheck |
| Credential leak | 5K–20K | CredentialLeakCheck |

**~9K tokens/session buys insurance against 3K–20K token mistakes.**

---

## Step 7: Add to CI

Add a drift check to your CI pipeline:

```yaml
# .github/workflows/drift.yml
name: Drift Guard
on: [push, pull_request]
jobs:
  drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: PYTHONPATH=src python3 -m drifter.cli check --format github
```

---

## Step 8: Iterate

After a week of use:

1. **Review the drift guard output.** Are there false positives? Add ignore patterns.
2. **Review the conductor.** Is it accurate? Are agents updating it?
3. **Review AGENTS.md.** Is it being read? Is it too long? Too short?
4. **Add custom checks.** Does your project have specific drift patterns? Write a check.

---

## Troubleshooting

### "drifter check shows too many warnings"

Add ignore patterns to `drifter.toml`:

```toml
[drifter.ignore]
paths = ["path/to/ignore/"]
```

Or disable checks you don't need:

```toml
[[drifter.checks]]
name = "digest_staleness"
enabled = false
```

### "Agents aren't reading AGENTS.md"

Shorten it. The optimal length is 150–250 lines. If it's longer, agents skip it. Move reference material to separate docs.

### "The conductor never gets updated"

Add conductor update to your agent's stop rule. Some agents need explicit prompting: "After finishing, update docs/project-conductor.md with evidence."

### "I have multiple projects"

Each project gets its own `AGENTS.md`, conductor, and session audit log (`<project>/.drifter/session.log`). Drifter is fully project-scoped. Run `drifter init` in each repo.

---

## Next Steps

- Read [`docs/rules-reference.md`](rules-reference.md) for the complete rule catalog
- Read [`docs/methodology.md`](methodology.md) for the philosophy
- Write your first custom check (see `src/drifter/drift_guard.py` for examples)
- Read `docs/methodology.md` for the philosophy behind each rule

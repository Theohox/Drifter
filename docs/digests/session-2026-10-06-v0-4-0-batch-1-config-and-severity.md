---
title: Session Digest — v0.4.0 Batch 1, Config Merge & Severity Ceiling
type: archive
status: archived
phase: 6
created: '2026-10-06T14:00:00Z'
updated: '2026-10-07T12:00:00Z'
---

# Session Digest — v0.4.0 Batch 1: Config Merge & Severity Ceiling

*Backfilled 2026-10-07 from CHANGELOG `[0.4.0]` (Fixed section) and the working tree. Written after the fact; details reconstructed from the changelog and code, not memory.*

## What We Did

First half of the v0.4.0 hardening release: fixed config semantics that were silently disabling checks, and wired the per-check severity config that had been parsed but never applied.

### 1. Config merge semantics (the silent-disable bug)

**Problem:** `[[drifter.checks]]` entries in `drifter.toml` / `pyproject.toml` replaced the entire check list instead of merging. A user writing a one-entry config to tweak a single check unknowingly disabled every other check — and got a reassuring 100/100 score from a suite of one.

**Solution:** `checks` entries now merge per `name` into `DEFAULT_CONFIG`: an entry updates the default entry of the same name (omitted fields keep their defaults); unknown names are appended. An explicit `checks = []` still disables the suite deliberately.

### 2. Severity ceiling

**Problem:** per-check `severity` config was parsed into `CheckConfig` but the engine only consulted `enabled`.

**Solution:** the engine now applies configured severity as a **ceiling** — a check's issues report at no higher severity than configured (demotion only; escalation intentionally unsupported). Default severities were curated to each check's maximum emitted severity (`pipeline_integrity`, `tree_integrity`, `file_size`, `claim_sync`, `no_rush` corrected from `warn` to `error`), so default behavior is unchanged.

### 3. Supporting fixes in the same batch

- Legacy `[tool.drifter]` section in `drifter.toml` honored again (older configs were silently ignored).
- Extension-named directories (e.g. `whisper.android.java` in vendored trees) no longer crash `credential_leak`, `git_safety`, `hardcoded_path` with `IsADirectoryError`; unreadable/binary files skipped.
- `is_ignored()` matches directory patterns as path-part subsequences (e.g. `frontend/src-tauri/sidecar/`), not just absolute-path substrings.
- `tree_integrity` skips `.mypy_cache` / `.ruff_cache`.
- Session heuristics: shared `is_test_run` / `is_drift_check` helpers — test runs require a word-boundary `pytest` match (no more "latest"/"protest" false positives); CHECK-action log entries always count as drift checks.
- `__main__.py` gained the missing `if __name__ == "__main__":` guard (no CLI execution on import).
- Root `CHANGELOG.md` exempted from doc validation (universal convention; it has no frontmatter).
- Stale documentation URL fixed — `drifter.toml` and its template point to `github.com/Theohox/Drifter`.

## Files Changed

| File | Change |
|------|--------|
| `src/drifter/config.py` | Per-name check merge, legacy section, curated severity defaults |
| `src/drifter/drift_guard.py` | Severity ceiling applied (`_cap_severity`) |
| `src/drifter/checks/behavioral.py` | Shared `is_test_run` / `is_drift_check` helpers |
| `src/drifter/checks/security.py`, `structure.py` | Directory/unreadable-file guards, cache skips |
| `src/drifter/__main__.py` | `__main__` guard |
| `src/drifter/_doc_validate.py` | Root `CHANGELOG.md` exemption |
| `drifter.toml`, `templates/drifter.toml.tmpl` | Repo URL fix |

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Tests | 251 | ~390 |
| Checks | 35 | 35 |
| Drift Score | 100/100 (misleading — sparse-config bug) | measured honestly |

## Decisions

1. **Ceiling, not floor, for severity.** Escalation via config would let a project paper over error-severity drift with higher-severity noise; demotion is the safe direction.
2. **Merge, don't replace, for check lists.** The replace semantics were the single most dangerous config behavior in the project — they turned a tuning knob into an off-switch.
3. **`checks = []` stays meaningful.** Disabling the whole suite must remain possible, but it must be explicit.

## Evidence

- CHANGELOG `[0.4.0]` Fixed section (2026-10-06)
- `pytest tests/ -q` green at release; 396 passed as of 2026-10-07

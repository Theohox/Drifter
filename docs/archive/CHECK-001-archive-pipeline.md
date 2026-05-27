---
title: "CHECK-001: Archive, pipeline, and skipped-file remediation"
type: archive
status: archived
phase: 0
created: '2026-05-27T00:00:00Z'
completed: '2026-05-27T17:45:00Z'
score: 100
task_id: CHECK-001
---

# CHECK-001: Archive, pipeline, and skipped-file remediation

## Evidence

- `drifter check` score: **100/100**
- All tests pass: **66/66**
- Templates synced to reflect 18 checks and 7-step pre-flight

## Decisions

- **Auto-archive on `mark_done()`** — completed tasks automatically move to `## Completed Tasks` table with timestamp
- **Pipeline columns** added to all task tables (backlog/ready/active/blocked/done)
- **Skipped-file remediation** — `dangerous_patterns.toml` patterns are respected by all checks
- **Semantic IDs** introduced: FEAT- (feature), CHECK- (drift guard check), PLUG- (plugin)

## Files Changed

- `src/drifter/conductor.py` — `mark_done()` auto-archives, `append_drift_score()` added
- `src/drifter/cli.py` — auto-updates conductor timestamps on `check` and `preflight`
- `templates/project-conductor.md.tmpl` — updated with pipeline columns
- `docs/project-conductor.md` — archive + pipeline columns live
- `tests/` — expanded to 66 tests

## Related Tasks

- Depends on: FEAT-001
- Leads to: CHECK-002

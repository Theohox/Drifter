---
title: "RELEASE-001: Final gates — session-log rotation, true drift score, release decision"
type: archive
status: archived
phase: 8
created: '2026-10-07T12:51:46Z'
updated: '2026-10-07T13:10:00Z'
completed: '2026-10-07T12:51:46Z'
score: 100
task_id: RELEASE-001
---

# RELEASE-001: Final gates — session-log rotation, true drift score, release decision

## Evidence

Log rotated; final gates green: 436 tests, ruff/format/mypy/vulture clean, drifter validate clean, wheel smoke-tested in scratch venv (init writes real templates, exit codes propagate), zennyvoice revalidated 0 crashes (147→142 issues after manifest regen + ghost_reference adopter fix). Final score 100/100 recorded in Drift Score History (2026-10-07T12:57). (Originally auto-archived with score 92 — the latest entry at that moment; corrected to the final verified score.)

## Decisions

- Folded all cleanup work into the single 0.4.0 release (never tagged/published before) rather than shipping a separate 0.4.1.
- Distribution renamed `drifter-check`; CLI stays `drifter`.

## Files Changed

- Whole-tree cleanup: see `docs/digests/session-2026-10-07-production-grade-cleanup.md` and CHANGELOG.md [0.4.0].

## Related Tasks

- Depends on: CLEANUP-002
- Leads to: Phase 9 (release tagging, SOW v3 adoption)

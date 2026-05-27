"""Pre-flight checklist runner.

Enforces the 6-step pre-flight protocol before any coding session.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from drifter.config import Config
from drifter.drift_guard import run_checks


@dataclass
class PreFlightResult:
    passed: bool
    step_results: list[dict[str, Any]] = field(default_factory=list)
    drift_score: int = 100
    errors: list[str] = field(default_factory=list)

    def print_report(self) -> None:
        print(f"\n{'='*60}")
        print("  PRE-FLIGHT REPORT")
        print(f"  {datetime.now(timezone.utc).isoformat()}")
        print(f"{'='*60}")

        for step in self.step_results:
            status = "✓" if step["passed"] else "✗"
            print(f"  [{status}] {step['name']}: {step['message']}")

        print(f"\n  Drift Score: {self.drift_score}/100")

        if self.passed:
            print("  ✓ Pre-flight PASSED. You may proceed.")
        else:
            print("  ✗ Pre-flight FAILED. Fix issues before coding.")
            for err in self.errors:
                print(f"    • {err}")

        print(f"{'='*60}\n")


def run_pre_flight(
    root: Path | None = None,
    config: Config | None = None,
    task: str | None = None,
) -> PreFlightResult:
    """Run the 6-step pre-flight protocol."""
    if config is None:
        config = Config.load(root)
    if root is None:
        root = config.root

    step_results: list[dict[str, Any]] = []
    errors: list[str] = []

    # Step 1: AGENTS.md exists and is readable
    agents_md = root / "AGENTS.md"
    if agents_md.exists():
        step_results.append({
            "name": "Read AGENTS.md",
            "passed": True,
            "message": f"Found {agents_md.relative_to(root)}",
        })
    else:
        step_results.append({
            "name": "Read AGENTS.md",
            "passed": False,
            "message": "AGENTS.md not found in repo root",
        })
        errors.append("AGENTS.md is missing. Create it from templates/AGENTS.md.tmpl")

    # Step 2: Session protocol exists
    session_protocol = root / "docs" / "session-protocol.md"
    if session_protocol.exists():
        step_results.append({
            "name": "Read Session Protocol",
            "passed": True,
            "message": f"Found {session_protocol.relative_to(root)}",
        })
    else:
        step_results.append({
            "name": "Read Session Protocol",
            "passed": False,
            "message": "docs/session-protocol.md not found",
        })
        errors.append("Session protocol is missing. Create it from templates/session-protocol.md.tmpl")

    # Step 3: Conductor exists
    conductor = root / "docs" / "project-conductor.md"
    if not conductor.exists():
        conductor = root / "project-conductor.md"
    if conductor.exists():
        step_results.append({
            "name": "Read Conductor",
            "passed": True,
            "message": f"Found {conductor.relative_to(root)}",
        })
    else:
        step_results.append({
            "name": "Read Conductor",
            "passed": False,
            "message": "project-conductor.md not found",
        })
        errors.append("Conductor is missing. Create it from templates/project-conductor.md.tmpl")

    # Step 4: Run drift guard
    try:
        report = run_checks(root, config)
        drift_passed = report.score >= config.drift_threshold
        step_results.append({
            "name": "Run Drift Guard",
            "passed": drift_passed,
            "message": f"Score: {report.score}/100 ({report.errors} errors, {report.warns} warns)",
        })
        if not drift_passed:
            errors.append(f"Drift score {report.score} is below threshold {config.drift_threshold}")
    except Exception as e:
        step_results.append({
            "name": "Run Drift Guard",
            "passed": False,
            "message": f"Failed to run: {e}",
        })
        errors.append(f"Drift guard failed: {e}")
        report = None

    # Step 5: Active task from conductor
    if conductor.exists():
        text = conductor.read_text(encoding="utf-8")
        has_active = "**Active Task**" in text or "## Active Task" in text
        has_blocked = "## Blocked Tasks" in text or "**Blocked Tasks**" in text
        if has_active:
            step_results.append({
                "name": "Pick Active Task",
                "passed": True,
                "message": "Conductor has an active task section",
            })
        else:
            step_results.append({
                "name": "Pick Active Task",
                "passed": False,
                "message": "Conductor has no active task",
            })
            errors.append("No active task in conductor. Add one before coding.")
    else:
        step_results.append({
            "name": "Pick Active Task",
            "passed": False,
            "message": "Cannot check without conductor",
        })

    # Step 6: Grep for existing code (informational only — can't enforce)
    step_results.append({
        "name": "Grep for Existing Code",
        "passed": True,
        "message": "Reminder: search codebase before writing new code",
    })

    passed = len(errors) == 0

    return PreFlightResult(
        passed=passed,
        step_results=step_results,
        drift_score=report.score if report else 0,
        errors=errors,
    )

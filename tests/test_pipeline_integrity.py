"""Tests for PipelineIntegrityCheck — the most complex check with zero coverage."""

from __future__ import annotations

from pathlib import Path

from drifter.config import Config
from drifter.checks.project import PipelineIntegrityCheck


class TestPipelineIntegrityCheck:
    def _conductor(self, tmp_path: Path, content: str) -> None:
        conductor = tmp_path / "docs" / "project-conductor.md"
        conductor.parent.mkdir(parents=True)
        conductor.write_text(f"---\ntype: backlog\n---\n\n{content}")

    def test_no_conductor_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        check = PipelineIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

    def test_task_in_active_and_blocked(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        self._conductor(
            tmp_path,
            "## Active Task\n\n"
            "| Field | Value |\n|-------|-------|\n"
            "| **ID** | FOO-001 |\n| **Name** | Active task |\n\n"
            "## Blocked Tasks\n\n"
            "| ID | Name | Pipeline | Blocked On | Reason |\n"
            "|----|------|----------|-----------|--------|\n"
            "| FOO-001 | Blocked task | backlog | design | reason |\n",
        )
        check = PipelineIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert any(
            "FOO-001" in i.detail and "both Active and Blocked" in i.detail
            for i in issues
        )

    def test_task_in_active_and_future(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        self._conductor(
            tmp_path,
            "## Active Task\n\n"
            "| Field | Value |\n|-------|-------|\n"
            "| **ID** | FOO-001 |\n| **Name** | Active task |\n\n"
            "## Future Tasks\n\n"
            "| ID | Name | Pipeline | Depends On | Status | Docs |\n"
            "|----|------|----------|-----------|--------|------|\n"
            "| FOO-001 | Future task | backlog | — | future | — |\n",
        )
        check = PipelineIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert any(
            "FOO-001" in i.detail and "both Active and Future" in i.detail
            for i in issues
        )

    def test_missing_depends_on_reference(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        self._conductor(
            tmp_path,
            "## Active Task\n\n"
            "| Field | Value |\n|-------|-------|\n"
            "| **ID** | FOO-001 |\n| **Depends On** | BAR-999 |\n\n",
        )
        check = PipelineIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert any(
            "BAR-999" in i.detail and "does not exist" in i.detail for i in issues
        )

    def test_circular_dependency(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        self._conductor(
            tmp_path,
            "## Blocked Tasks\n\n"
            "| ID | Name | Pipeline | Blocked On | Reason |\n"
            "|----|------|----------|-----------|--------|\n"
            "| A-001 | Task A | backlog | B-001 | reason |\n"
            "| B-001 | Task B | backlog | A-001 | reason |\n",
        )
        check = PipelineIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert any("Circular dependency" in i.detail for i in issues)

    def test_next_reference_missing(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        self._conductor(
            tmp_path,
            "## Active Task\n\n"
            "| Field | Value |\n|-------|-------|\n"
            "| **ID** | FOO-001 |\n| **Next** | BAR-999: desc |\n\n",
        )
        check = PipelineIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert any("BAR-999" in i.detail and "Next" in i.detail for i in issues)

    def test_blocked_task_empty_blocked_on(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        self._conductor(
            tmp_path,
            "## Blocked Tasks\n\n"
            "| ID | Name | Pipeline | Blocked On | Reason |\n"
            "|----|------|----------|-----------|--------|\n"
            "| FOO-001 | Task | backlog | — | reason |\n",
        )
        check = PipelineIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert any(
            "FOO-001" in i.detail and "empty 'Blocked On'" in i.detail for i in issues
        )

    def test_completed_task_empty_evidence(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        self._conductor(
            tmp_path,
            "## Completed Tasks\n\n"
            "| ID | Name | Completed | Archive | Score |\n"
            "|----|------|-----------|---------|-------|\n"
            "| FOO-001 | Task | 2026-01-01 | — | — |\n",
        )
        check = PipelineIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert any(
            "FOO-001" in i.detail and "empty evidence" in i.detail for i in issues
        )

    def test_valid_conductor_passes(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        self._conductor(
            tmp_path,
            "## Active Task\n\n"
            "| Field | Value |\n|-------|-------|\n"
            "| **ID** | FOO-001 |\n| **Depends On** | — |\n| **Next** | — |\n\n"
            "## Blocked Tasks\n\n"
            "| ID | Name | Pipeline | Blocked On | Reason |\n"
            "|----|------|----------|-----------|--------|\n"
            "| BAR-001 | Task | backlog | design | reason |\n\n"
            "## Completed Tasks\n\n"
            "| ID | Name | Completed | Archive | Score |\n"
            "|----|------|-----------|---------|-------|\n"
            "| BAZ-001 | Task | 2026-01-01 | archive | 100/100 |\n",
        )
        check = PipelineIntegrityCheck()
        issues = check.run(tmp_path, config)
        assert len(issues) == 0

"""Tests for conductor manager."""

import re
from pathlib import Path

from drifter.config import Config
from drifter.conductor import Conductor


class TestConductor:
    def test_init_creates_file(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        conductor = Conductor(root=tmp_path, config=config)
        path = conductor.init()
        assert path.exists()

    def test_show_reads_active_task(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        conductor = Conductor(root=tmp_path, config=config)
        conductor.init()
        info = conductor.show()
        assert "error" not in info
        assert "phase" in info

    def test_mark_done_updates_status(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        conductor = Conductor(root=tmp_path, config=config)
        conductor.init()
        success = conductor.mark_done("0.1", "tests pass")
        assert success
        text = conductor.read()
        assert "✅ COMPLETE" in text
        assert "tests pass" in text

    def test_block_task_adds_row(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        conductor = Conductor(root=tmp_path, config=config)
        conductor.init()
        success = conductor.block_task("0.2", "needs design review")
        assert success
        text = conductor.read()
        assert "needs design review" in text

    def test_touch_timestamp_updates_updated_field(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        conductor = Conductor(root=tmp_path, config=config)
        conductor.init()
        stale = re.sub(
            r"updated: '[^']*'", "updated: '2000-01-01T00:00:00Z'", conductor.read()
        )
        conductor.path.write_text(stale, encoding="utf-8")
        conductor.show()  # public entry point that touches the timestamp
        refreshed = conductor.read()
        assert "2000-01-01" not in refreshed
        assert re.search(r"updated: '\d{4}-\d{2}-\d{2}T", refreshed)

    def test_append_drift_score_adds_row(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        conductor = Conductor(root=tmp_path, config=config)
        conductor.init()
        conductor.append_drift_score(95, tests=21, notes="good run")
        text = conductor.read()
        assert "95/100" in text
        assert "21" in text
        assert "good run" in text

    def test_mark_done_creates_archive_file(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        conductor = Conductor(root=tmp_path, config=config)
        conductor.init()
        success = conductor.mark_done("FEAT-001", "tests pass")
        assert success
        archive_file = tmp_path / "docs" / "archive" / "FEAT-001-initialize-project.md"
        assert archive_file.exists()
        text = archive_file.read_text(encoding="utf-8")
        assert "type: archive" in text
        assert "task_id: FEAT-001" in text
        assert "tests pass" in text

    def test_mark_done_records_real_drift_score(self, tmp_path: Path) -> None:
        """The archive gets the latest measured score, never a fabricated one."""
        config = Config.load(root=tmp_path)
        conductor = Conductor(root=tmp_path, config=config)
        conductor.init()
        conductor.append_drift_score(72, tests=10, notes="preflight")
        assert conductor.mark_done("FEAT-001", "tests pass")
        archive_file = tmp_path / "docs" / "archive" / "FEAT-001-initialize-project.md"
        assert "score: 72" in archive_file.read_text(encoding="utf-8")

    def test_mark_done_omits_score_without_history(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        conductor = Conductor(root=tmp_path, config=config)
        conductor.init()
        assert conductor.mark_done("FEAT-001", "tests pass")
        archive_file = tmp_path / "docs" / "archive" / "FEAT-001-initialize-project.md"
        assert "score:" not in archive_file.read_text(encoding="utf-8")

    def test_mark_done_strips_table_pipe_from_task_name(self, tmp_path: Path) -> None:
        """The Active Task row's closing `|` must not leak into the archive title."""
        config = Config.load(root=tmp_path)
        conductor = Conductor(root=tmp_path, config=config)
        conductor.init()
        assert conductor.mark_done("FEAT-001", "tests pass")
        archive_file = tmp_path / "docs" / "archive" / "FEAT-001-initialize-project.md"
        text = archive_file.read_text(encoding="utf-8")
        assert 'title: "FEAT-001: Initialize project"' in text
        assert "# FEAT-001: Initialize project\n" in text

    def test_mark_done_root_layout_archive_link(self, tmp_path: Path) -> None:
        """Conductor at repo root: archive link must be docs/archive/..."""
        config = Config.load(root=tmp_path)
        conductor = Conductor(root=tmp_path, config=config)
        conductor.path = tmp_path / "project-conductor.md"
        conductor.init()
        assert conductor.mark_done("FEAT-001", "tests pass")
        text = conductor.read()
        assert "[archive](docs/archive/FEAT-001-initialize-project.md)" in text

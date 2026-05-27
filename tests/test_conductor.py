"""Tests for conductor manager."""

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

    def test_touch_timestamp_no_crash(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        conductor = Conductor(root=tmp_path, config=config)
        conductor.init()
        # Should not raise
        conductor._touch_timestamp()

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

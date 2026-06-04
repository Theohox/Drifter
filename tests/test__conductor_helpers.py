"""Tests for conductor helper functions."""

from pathlib import Path

from drifter._conductor_helpers import (
    _slugify,
    create_archive_file,
    default_conductor_content,
)


class TestSlugify:
    def test_basic(self) -> None:
        assert _slugify("Hello World") == "hello-world"

    def test_punctuation_removed(self) -> None:
        assert _slugify("Foo: Bar!") == "foo-bar"

    def test_truncated(self) -> None:
        assert len(_slugify("a" * 100)) == 50


class TestCreateArchiveFile:
    def test_creates_file(self, tmp_path: Path) -> None:
        archive = create_archive_file(tmp_path, "TASK-001", "Do thing", "tests pass")
        assert archive is not None
        assert archive.exists()
        text = archive.read_text()
        assert "TASK-001: Do thing" in text
        assert "tests pass" in text

    def test_filename_slug(self, tmp_path: Path) -> None:
        archive = create_archive_file(tmp_path, "FEAT-001", "Add feature X", "done")
        assert archive is not None
        assert "FEAT-001-add-feature-x" in archive.name


class TestDefaultConductorContent:
    def test_has_structure(self) -> None:
        content = default_conductor_content()
        assert "## Current Phase" in content
        assert "## Active Task" in content
        assert "## Blocked Tasks" in content
        assert "## Drift Score History" in content

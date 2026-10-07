"""Tests for shared check helpers (checks/_shared.py)."""

from pathlib import Path

from drifter.checks._shared import (
    archive_designated_docs,
    is_skippable_path,
    load_drifter_manifest,
    resolve_doc_path,
)


class TestIsSkippablePath:
    def test_placeholder_patterns_skipped(self) -> None:
        assert is_skippable_path("docs/your_file.md")
        assert is_skippable_path("https://example.com/x.md")
        assert is_skippable_path("src/nonexistent/module.py")

    def test_real_paths_not_skipped(self) -> None:
        assert not is_skippable_path("src/drifter/config.py")
        assert not is_skippable_path("docs/architecture.md")


class TestResolveDocPath:
    def test_root_path_preferred(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        assert resolve_doc_path(tmp_path, "src") == tmp_path / "src"

    def test_docs_fallback(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        (docs / "guides").mkdir(parents=True)
        assert resolve_doc_path(tmp_path, "guides") == docs / "guides"

    def test_missing_returns_docs_candidate(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        assert resolve_doc_path(tmp_path, "nope") == tmp_path / "docs" / "nope"


class TestLoadDrifterManifest:
    def test_missing_manifest_returns_none_no_issue(self, tmp_path: Path) -> None:
        manifest, issue = load_drifter_manifest(tmp_path, "some_check")
        assert manifest is None
        assert issue is None

    def test_corrupted_manifest_returns_error_issue(self, tmp_path: Path) -> None:
        (tmp_path / "drifter-manifest.toml").write_text("[broken\n")
        manifest, issue = load_drifter_manifest(tmp_path, "some_check")
        assert manifest is None
        assert issue is not None
        assert issue.check == "some_check"
        assert issue.severity == "error"
        assert "Cannot parse" in issue.detail

    def test_valid_manifest_returned(self, tmp_path: Path) -> None:
        (tmp_path / "drifter-manifest.toml").write_text("[checks]\ncount = 2\n")
        manifest, issue = load_drifter_manifest(tmp_path, "some_check")
        assert issue is None
        assert manifest is not None
        assert manifest["checks"]["count"] == 2


class TestArchiveDesignatedDocs:
    def test_collects_archive_entries(self) -> None:
        manifest = {
            "tree": {
                "docs": {
                    "guide.md": {"type": "guide"},
                    "old.md": {"type": "archive"},
                    "digests": {
                        "session-1.md": {"type": "archive"},
                        "index.md": {"type": "snapshot"},
                    },
                }
            }
        }
        assert archive_designated_docs(manifest) == {
            "old.md",
            "digests/session-1.md",
        }

    def test_empty_when_no_docs_tree(self) -> None:
        assert archive_designated_docs({}) == set()

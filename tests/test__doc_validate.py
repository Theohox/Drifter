"""Tests for document validation internals."""

from pathlib import Path

from drifter._doc_validate import _parse_frontmatter, _validate_single


class TestParseFrontmatter:
    def test_simple_pairs(self) -> None:
        text = "type: backlog\nstatus: active\n"
        result = _parse_frontmatter(text)
        assert result == {"type": "backlog", "status": "active"}

    def test_ignores_comments(self) -> None:
        text = "# comment\ntype: guide\n"
        result = _parse_frontmatter(text)
        assert result == {"type": "guide"}


class TestValidateSingle:
    def test_missing_frontmatter(self, tmp_path: Path) -> None:
        doc = tmp_path / "readme.md"
        doc.write_text("# Hello\n")
        issues = _validate_single(doc, tmp_path)
        assert any("Missing YAML frontmatter" in i.detail for i in issues)

    def test_valid_frontmatter_passes(self, tmp_path: Path) -> None:
        doc = tmp_path / "readme.md"
        doc.write_text(
            "---\ntype: guide\nstatus: active\ntitle: T\ncreated: '2026-01-01'\nupdated: '2026-01-01'\n---\n# Hello\n"
        )
        issues = _validate_single(doc, tmp_path)
        assert len(issues) == 0

"""Tests for document validator."""

from pathlib import Path

from drifter.config import Config
from drifter.doc_validator import validate_docs


class TestDocValidator:
    def test_missing_frontmatter(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        doc = tmp_path / "docs" / "test.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# No frontmatter\n")

        report = validate_docs(root=tmp_path, config=config)
        assert report.errors >= 1
        assert any("Missing YAML frontmatter" in i.detail for i in report.issues)

    def test_valid_document(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        doc = tmp_path / "docs" / "test.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("""---
title: Test
type: guide
status: active
created: '2026-01-01T00:00:00Z'
updated: '2026-01-02T00:00:00Z'
---

# Test
""")
        report = validate_docs(root=tmp_path, config=config)
        assert report.errors == 0

    def test_invalid_type(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        doc = tmp_path / "docs" / "test.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("""---
title: Test
type: invalid_type
status: active
created: '2026-01-01T00:00:00Z'
updated: '2026-01-02T00:00:00Z'
---

# Test
""")
        report = validate_docs(root=tmp_path, config=config)
        assert any("Invalid type" in i.detail for i in report.issues)

    def test_updated_before_created(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        doc = tmp_path / "docs" / "test.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("""---
title: Test
type: guide
status: active
created: '2026-01-02T00:00:00Z'
updated: '2026-01-01T00:00:00Z'
---

# Test
""")
        report = validate_docs(root=tmp_path, config=config)
        assert any("older than 'created'" in i.detail for i in report.issues)

    def test_missing_status(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        doc = tmp_path / "docs" / "test.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("""---
title: Test
type: guide
created: '2026-01-01T00:00:00Z'
updated: '2026-01-02T00:00:00Z'
---

# Test
""")
        report = validate_docs(root=tmp_path, config=config)
        assert any("Missing 'status:'" in i.detail for i in report.issues)

    def test_invalid_status(self, tmp_path: Path) -> None:
        config = Config.load(root=tmp_path)
        doc = tmp_path / "docs" / "test.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("""---
title: Test
type: guide
status: unknown
created: '2026-01-01T00:00:00Z'
updated: '2026-01-02T00:00:00Z'
---

# Test
""")
        report = validate_docs(root=tmp_path, config=config)
        assert any("Invalid status" in i.detail for i in report.issues)

"""Tests for the bundled template resolver."""

from __future__ import annotations

import drifter._templates as templates_mod
from drifter._templates import template_text

BUNDLED_TEMPLATES = [
    "AGENTS.md.tmpl",
    "archive-readme.md.tmpl",
    "dangerous_patterns.toml.tmpl",
    "digest-index.md.tmpl",
    "drifter.toml.tmpl",
    "project-conductor.md.tmpl",
    "session-protocol.md.tmpl",
]


class _Missing:
    """Traversable stand-in where nothing exists."""

    def joinpath(self, _part: str) -> _Missing:
        return self

    def is_file(self) -> bool:
        return False


class TestTemplateText:
    def test_all_bundled_templates_resolve(self) -> None:
        for name in BUNDLED_TEMPLATES:
            text = template_text(name)
            assert text is not None, f"{name} not resolvable"
            assert text.strip(), f"{name} is empty"

    def test_unknown_template_returns_none(self) -> None:
        assert template_text("does-not-exist.tmpl") is None

    def test_none_when_package_data_and_checkout_fallback_missing(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr(templates_mod.resources, "files", lambda _pkg: _Missing())
        assert template_text("AGENTS.md.tmpl") is None

"""Resolve bundled template files (package data with a dev-checkout fallback)."""

from __future__ import annotations

from importlib import resources
from pathlib import Path


def template_text(name: str) -> str | None:
    """Return the contents of bundled template `name`, or None if missing.

    Resolves via importlib.resources, which works for installed wheels and
    editable installs. Falls back to a repo-root templates/ directory so a
    bare source checkout without any install still works.
    """
    ref = resources.files("drifter").joinpath("templates").joinpath(name)
    try:
        if ref.is_file():
            return ref.read_text(encoding="utf-8")
    except (FileNotFoundError, NotADirectoryError, OSError):
        pass
    fallback = Path(__file__).resolve().parent.parent.parent / "templates" / name
    if fallback.is_file():
        return fallback.read_text(encoding="utf-8")
    return None

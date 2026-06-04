"""Safe TOML loading utilities."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def safe_load_toml(path: Path) -> dict[str, Any] | None:
    """Load TOML from path, returning None on any parse or read error.

    Callers should treat None as "file is unreadable or corrupted"
    and emit a graceful error rather than crashing.
    """
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError, ValueError):
        return None

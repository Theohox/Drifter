"""Base types for drift checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from drifter.config import Config


@dataclass(frozen=True)
class Issue:
    check: str
    file: str
    detail: str
    severity: str = "warn"  # "error" | "warn" | "info"

    def __repr__(self) -> str:
        return f"[{self.severity.upper()}] {self.check}: {self.file} — {self.detail}"


class Check(Protocol):
    name: str

    def run(self, root: Path, config: Config) -> list[Issue]: ...

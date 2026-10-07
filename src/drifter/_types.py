"""Shared types for the Drifter enforcement layer.

Classification lives here (not in shell_guard or errors) so that both
modules can import it without a circular dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ClassificationAction = Literal["allow", "block", "warn", "approval_required"]


@dataclass(frozen=True)
class Classification:
    action: ClassificationAction
    reason: str
    matched_pattern: str | None = None

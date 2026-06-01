"""Structured exceptions for Drifter enforcement layer.

These exceptions carry metadata so any integration (MCP, Kimi, custom hooks)
can handle enforcement failures programmatically.
"""

from __future__ import annotations

from dataclasses import dataclass

from drifter.shell_guard import Classification


@dataclass
class DangerousCommandError(Exception):
    """Raised when a command matches a blocked pattern."""

    command: str
    pattern: str | None
    reason: str
    classification: Classification

    def __str__(self) -> str:
        return f"BLOCKED: {self.reason} (command: '{self.command}')"


@dataclass
class ApprovalRequiredError(Exception):
    """Raised when a command requires explicit human approval."""

    command: str
    pattern: str | None
    reason: str
    classification: Classification

    def __str__(self) -> str:
        return f"APPROVAL REQUIRED: {self.reason} (command: '{self.command}')"

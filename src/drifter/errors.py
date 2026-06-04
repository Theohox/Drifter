"""Structured exceptions for Drifter enforcement layer.

These exceptions carry metadata so any integration (MCP, Kimi, custom hooks)
can handle enforcement failures programmatically.
"""

from __future__ import annotations

from drifter.shell_guard import Classification


class DrifterError(Exception):
    """Base for all Drifter enforcement errors."""

    def __init__(
        self,
        command: str,
        pattern: str | None,
        reason: str,
        classification: Classification,
    ) -> None:
        self.command = command
        self.pattern = pattern
        self.reason = reason
        self.classification = classification
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        return f"{self.__class__.__name__}: {self.reason} (command: '{self.command}')"


class DangerousCommandError(DrifterError):
    """Raised when a command matches a blocked pattern."""
    pass


class ApprovalRequiredError(DrifterError):
    """Raised when a command requires explicit human approval."""
    pass

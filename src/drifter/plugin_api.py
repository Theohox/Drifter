"""Reusable tool interceptor for Drifter integrations.

Any plugin (MCP server, Kimi CLI hook, custom integration) can import
ToolInterceptor to auto-populate the session log and enforce dangerous_patterns
before tool calls execute.
"""

from __future__ import annotations

from pathlib import Path

from drifter.config import Config
from drifter.errors import DangerousCommandError
from drifter.session_logger import SessionLogger
from drifter.shell_guard import Classification, ShellGuard


class ToolInterceptor:
    """Intercept tool calls, log them, and enforce dangerous_patterns."""

    def __init__(self, root: Path | None = None):
        self.root = (root or Path(".")).resolve()
        self.config = Config.load(root=self.root)
        self._guard = ShellGuard(root=self.root)

    def before_read(self, path: Path) -> None:
        """Log a READ action to the session audit log."""
        logger = SessionLogger(root=self.root)
        logger.log("READ", str(path))

    def before_write(self, path: Path) -> None:
        """Log a WRITE action to the session audit log."""
        logger = SessionLogger(root=self.root)
        logger.log("WRITE", str(path))

    def before_shell(self, command: str) -> Classification:
        """Log a SHELL action and enforce dangerous_patterns.

        Raises DangerousCommandError if the command is blocked.
        Returns the Classification for allowed/warned commands.
        """
        logger = SessionLogger(root=self.root)
        logger.log("SHELL", command)
        return self._guard.enforce(command)

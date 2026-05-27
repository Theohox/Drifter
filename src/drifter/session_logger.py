"""Session audit logger.

Records every tool call to an append-only log.
Checks verify behavioral patterns from the log.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class LogEntry:
    timestamp: str
    action: str
    target: str


class SessionLogger:
    """Append-only session log for agent tool calls."""

    def __init__(self, path: Path | None = None):
        self.path = path or (Path.home() / ".drifter" / "session.log")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, action: str, target: str) -> None:
        """Append a single entry to the session log."""
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = f"[{timestamp}] {action} {target}\n"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(entry)

    def read_entries(self) -> list[LogEntry]:
        """Read all entries from the session log."""
        if not self.path.exists():
            return []
        entries: list[LogEntry] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Parse [timestamp] action target
                if line.startswith("[") and "]" in line:
                    timestamp_end = line.index("]")
                    timestamp = line[1:timestamp_end]
                    rest = line[timestamp_end + 1 :].strip()
                    parts = rest.split(" ", 1)
                    action = parts[0]
                    target = parts[1] if len(parts) > 1 else ""
                    entries.append(LogEntry(timestamp, action, target))
        return entries

    def clear(self) -> None:
        """Clear the session log. Called at session start."""
        if self.path.exists():
            self.path.write_text("")

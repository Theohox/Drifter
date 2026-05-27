"""Session capture — records what happened during an agent session.

Lightweight alternative to claude-mem. Stores session metadata locally.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Session:
    id: str
    started_at: str
    ended_at: str | None = None
    task_id: str | None = None
    task_name: str | None = None
    files_touched: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    drift_score_before: int | None = None
    drift_score_after: int | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        return cls(**data)


class SessionStore:
    """Simple JSON-based session store."""

    def __init__(self, root: Path | None = None):
        self.root = (root or Path(".")).resolve()
        self.dir = self.root / ".drifter" / "sessions"
        self.dir.mkdir(parents=True, exist_ok=True)

    def save(self, session: Session) -> Path:
        path = self.dir / f"{session.id}.json"
        path.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
        return path

    def load(self, session_id: str) -> Session | None:
        path = self.dir / f"{session_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Session.from_dict(data)

    def list_sessions(self) -> list[Session]:
        sessions = []
        for path in sorted(self.dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            sessions.append(Session.from_dict(data))
        return sessions

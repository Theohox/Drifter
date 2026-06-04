"""Session audit logger.

Records every tool call to an append-only log with HMAC integrity.
Checks verify behavioral patterns from the log.
"""

from __future__ import annotations

import hmac
import hashlib
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class LogEntry:
    timestamp: str
    action: str
    target: str
    pid: int = 0
    verified: bool = False


class SessionLogger:
    """Append-only session log for agent tool calls.

    Entries are HMAC-signed to detect tampering. The secret is derived
    per-repo and stored with restrictive permissions.
    """

    def __init__(self, path: Path | None = None, root: Path | None = None):
        if path is not None:
            self.path = path
        elif root is not None:
            self.path = root / ".drifter" / "session.log"
        else:
            self.path = Path.home() / ".drifter" / "session.log"

        # Restrict .drifter/ to owner only (0o700)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            self.path.parent.chmod(stat.S_IRWXU)

        self._secret = self._derive_secret()

    def _derive_secret(self) -> bytes:
        """Derive a per-repo HMAC secret."""
        secret_path = self.path.parent / ".session_secret"
        if secret_path.exists():
            return secret_path.read_bytes()
        secret = os.urandom(32)
        secret_path.write_bytes(secret)
        if os.name != "nt":
            secret_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        return secret

    def _sign(self, body: str) -> str:
        """Create HMAC-SHA256 signature truncated to 16 hex chars."""
        sig = hmac.new(self._secret, body.encode(), hashlib.sha256).hexdigest()
        return sig[:16]

    def log(self, action: str, target: str) -> None:
        """Append a signed entry to the session log."""
        timestamp = datetime.now(timezone.utc).isoformat()
        pid = os.getpid()
        body = f"{timestamp}|{pid}|{action}|{target}"
        sig = self._sign(body)
        entry = f"[{body}|{sig}]\n"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(entry)
        if os.name != "nt":
            self.path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600

    def read_entries(self) -> list[LogEntry]:
        """Read and verify entries from the session log.

        Skips tampered entries. Falls back to legacy format for
        backward compatibility, marking those as unverified.
        """
        if not self.path.exists():
            return []
        entries: list[LogEntry] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # New format: [timestamp|pid|action|target|sig]
                if line.startswith("[") and line.endswith("]") and line.count("|") >= 4:
                    inner = line[1:-1]
                    parts = inner.rsplit("|", 1)
                    if len(parts) == 2:
                        body, sig = parts
                        expected = self._sign(body)
                        if hmac.compare_digest(expected, sig):
                            ts, pid_str, action, target = body.split("|", 3)
                            entries.append(LogEntry(ts, action, target, int(pid_str), True))
                        # else: tampered entry — silently skip
                        continue
                # Legacy format: [timestamp] action target
                if line.startswith("[") and "]" in line:
                    timestamp_end = line.index("]")
                    timestamp = line[1:timestamp_end]
                    rest = line[timestamp_end + 1 :].strip()
                    parts = rest.split(" ", 1)
                    action = parts[0]
                    target = parts[1] if len(parts) > 1 else ""
                    entries.append(LogEntry(timestamp, action, target, 0, False))
        return entries

    def rotate_log(self) -> Path | None:
        """Rotate the session log — archive current, start fresh.

        Returns the path to the archived log, or None if there was
        nothing to rotate.
        """
        if not self.path.exists() or self.path.stat().st_size == 0:
            return None
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        archive = self.path.with_suffix(f".log.{timestamp}")
        self.path.rename(archive)
        return archive

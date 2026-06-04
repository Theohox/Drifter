"""Cross-platform shell history reader.

Supports bash, zsh, and fish history formats with auto-detection.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable


class HistoryReader:
    """Read shell history files across bash, zsh, and fish."""

    def __init__(self, path: Path | None = None):
        self.path = path
        self.shell = self._detect_shell()

    @classmethod
    def auto_detect(cls) -> "HistoryReader | None":
        """Auto-detect history file from environment and known paths."""
        # 1. Check explicit env var
        env_path = os.environ.get("DRIFTER_HISTORY_PATH")
        if env_path:
            p = Path(env_path).expanduser()
            if p.exists():
                return cls(p)

        # 2. Check SHELL env var
        shell = os.environ.get("SHELL", "").lower()
        if "fish" in shell:
            p = Path.home() / ".local/share/fish/fish_history"
            if p.exists():
                return cls(p)
        if "zsh" in shell:
            p = Path.home() / ".zsh_history"
            if p.exists():
                return cls(p)
        if "bash" in shell:
            p = Path.home() / ".bash_history"
            if p.exists():
                return cls(p)

        # 3. Fall back to known paths (any shell)
        for candidate in [
            Path.home() / ".bash_history",
            Path.home() / ".zsh_history",
            Path.home() / ".local/share/fish/fish_history",
        ]:
            if candidate.exists():
                return cls(candidate)

        return None

    def _detect_shell(self) -> str:
        """Detect shell type from path or content."""
        if self.path is None:
            return "unknown"

        name = self.path.name.lower()
        if "fish" in name:
            return "fish"
        if "zsh" in name:
            return "zsh"
        if "bash" in name:
            return "bash"

        # Heuristic from content
        try:
            text = self.path.read_text(encoding="utf-8", errors="ignore")
            if text.startswith("- cmd:"):
                return "fish"
            if re.search(r"^:\s+\d+:\d+;", text, re.MULTILINE):
                return "zsh"
        except Exception:
            pass

        return "bash"  # default assumption

    def read_commands(self, max_entries: int | None = None) -> list[str]:
        """Read and return list of command strings."""
        if self.path is None or not self.path.exists():
            return []

        text = self.path.read_text(encoding="utf-8", errors="ignore")
        commands: list[str] = []

        if self.shell == "fish":
            commands = self._parse_fish(text)
        elif self.shell == "zsh":
            commands = self._parse_zsh(text)
        else:
            commands = self._parse_bash(text)

        if max_entries is not None and len(commands) > max_entries:
            commands = commands[-max_entries:]

        return commands

    def _parse_bash(self, text: str) -> list[str]:
        """Parse bash history — one command per line."""
        commands = []
        for line in text.split("\n"):
            line = line.strip()
            if line:
                commands.append(line)
        return commands

    def _parse_zsh(self, text: str) -> list[str]:
        """Parse zsh history — may have timestamps `: 1234567890:0;command`."""
        commands = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Strip extended history timestamp
            match = re.match(r"^:\s+\d+:\d+;(.+)$", line)
            if match:
                commands.append(match.group(1))
            else:
                commands.append(line)
        return commands

    def _parse_fish(self, text: str) -> list[str]:
        """Parse fish history — YAML-like with `- cmd:` entries."""
        commands = []
        for line in text.split("\n"):
            line = line.strip()
            match = re.match(r"^-\s+cmd:\s+(.+)$", line)
            if match:
                commands.append(match.group(1))
        return commands

    def __repr__(self) -> str:
        return f"HistoryReader(path={self.path}, shell={self.shell})"

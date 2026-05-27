"""Session compressor — compresses session data into a digest.

Optional: requires an LLM call for semantic compression.
Without an LLM, falls back to structured summary.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from drifter.memory.session_capture import Session


@dataclass
class Digest:
    title: str
    summary: str
    decisions: list[str]
    files_changed: list[str]
    drift_score_delta: int | None


class Compressor:
    """Compress a session into a digest."""

    def compress(self, session: Session) -> Digest:
        """Create a digest from session data.

        This is a rule-based compressor. For LLM-based compression,
        subclass and override this method.
        """
        title = session.task_name or "Untitled session"
        if session.started_at:
            date = session.started_at[:10]
            title = f"{date} — {title}"

        summary_parts = [
            f"Session {session.id}",
        ]
        if session.task_id:
            summary_parts.append(f"Task: {session.task_id}")
        if session.files_touched:
            summary_parts.append(f"Files touched: {', '.join(session.files_touched)}")
        if session.tools_used:
            summary_parts.append(f"Tools used: {', '.join(session.tools_used)}")

        drift_delta = None
        if session.drift_score_before is not None and session.drift_score_after is not None:
            drift_delta = session.drift_score_after - session.drift_score_before
            summary_parts.append(f"Drift score: {session.drift_score_before} → {session.drift_score_after} ({drift_delta:+,})")

        summary = "\n".join(summary_parts)

        decisions = []
        if session.notes:
            decisions = [line.strip("- ") for line in session.notes.split("\n") if line.strip().startswith("-")]

        return Digest(
            title=title,
            summary=summary,
            decisions=decisions,
            files_changed=session.files_touched,
            drift_score_delta=drift_delta,
        )

    def to_markdown(self, digest: Digest) -> str:
        lines = [
            f"# {digest.title}",
            "",
            "## Summary",
            "",
            digest.summary,
            "",
        ]
        if digest.decisions:
            lines.extend([
                "## Decisions",
                "",
            ])
            for decision in digest.decisions:
                lines.append(f"- {decision}")
            lines.append("")
        if digest.files_changed:
            lines.extend([
                "## Files Changed",
                "",
            ])
            for f in digest.files_changed:
                lines.append(f"- `{f}`")
            lines.append("")
        if digest.drift_score_delta is not None:
            lines.extend([
                "## Drift Impact",
                "",
                f"Drift score delta: {digest.drift_score_delta:+,}",
                "",
            ])
        return "\n".join(lines)

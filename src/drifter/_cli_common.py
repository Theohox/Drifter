"""Shared presentation helpers for CLI handlers."""

from __future__ import annotations


def print_banner(title: str) -> None:
    """Print the standard 60-column section banner used across CLI commands."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_rule() -> None:
    """Print the standard 60-column closing rule used across CLI commands."""
    print(f"{'=' * 60}\n")

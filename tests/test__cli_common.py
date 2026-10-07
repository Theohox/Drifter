"""Tests for shared CLI presentation helpers."""

from __future__ import annotations

from drifter._cli_common import print_banner, print_rule


def test_print_banner(capsys) -> None:
    print_banner("HELLO")
    out = capsys.readouterr().out
    assert "  HELLO" in out
    assert out.count("=" * 60) == 2


def test_print_rule(capsys) -> None:
    print_rule()
    out = capsys.readouterr().out
    assert out.strip() == "=" * 60

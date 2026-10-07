"""Tests for CLI parser construction and dispatch (drifter.cli)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from drifter import cli

HANDLER_NAMES = [
    "cmd_audit",
    "cmd_check",
    "cmd_conductor",
    "cmd_describe",
    "cmd_init",
    "cmd_install_hook",
    "cmd_log",
    "cmd_log_rotate",
    "cmd_manifest",
    "cmd_preflight",
    "cmd_session_report",
    "cmd_uninstall_hook",
    "cmd_validate",
]


@pytest.fixture
def spies(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    """Replace every command handler with a spy returning 0."""
    spies: dict[str, MagicMock] = {}
    for name in HANDLER_NAMES:
        spy = MagicMock(return_value=0)
        monkeypatch.setattr(cli, name, spy)
        spies[name] = spy
    return spies


@pytest.mark.parametrize(
    ("argv", "handler_name"),
    [
        (["check"], "cmd_check"),
        (["check", "--score"], "cmd_check"),
        (["check", "--json"], "cmd_check"),
        (["check", "--format", "github"], "cmd_check"),
        (["preflight"], "cmd_preflight"),
        (["preflight", "--task", "x", "--keyword", "y"], "cmd_preflight"),
        (["conductor", "init"], "cmd_conductor"),
        (["conductor", "init", "--force"], "cmd_conductor"),
        (["conductor", "show"], "cmd_conductor"),
        (["conductor", "done", "--task-id", "T-1"], "cmd_conductor"),
        (["conductor", "block", "--task-id", "T-1", "--reason", "r"], "cmd_conductor"),
        (["conductor", "next"], "cmd_conductor"),
        (["validate"], "cmd_validate"),
        (["audit"], "cmd_audit"),
        (["audit", "--no-history", "--window", "5"], "cmd_audit"),
        (["init"], "cmd_init"),
        (["init", "--full", "--force"], "cmd_init"),
        (["log", "READ", "foo.py"], "cmd_log"),
        (["log-rotate"], "cmd_log_rotate"),
        (["session-report"], "cmd_session_report"),
        (["install-hook"], "cmd_install_hook"),
        (["uninstall-hook"], "cmd_uninstall_hook"),
        (["manifest"], "cmd_manifest"),
        (["describe"], "cmd_describe"),
        (["describe", "--format", "markdown"], "cmd_describe"),
    ],
)
def test_dispatch_routes_to_handler(
    spies: dict[str, MagicMock], argv: list[str], handler_name: str
) -> None:
    rc = cli.main(argv)
    assert rc == 0
    spies[handler_name].assert_called_once()
    for name, spy in spies.items():
        if name != handler_name:
            spy.assert_not_called()


def test_handler_return_code_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "cmd_check", MagicMock(return_value=7))
    assert cli.main(["check"]) == 7


def test_root_flag_propagates(spies: dict[str, MagicMock], tmp_path: Path) -> None:
    cli.main(["--root", str(tmp_path), "check"])
    assert spies["cmd_check"].call_args.args[0].root == tmp_path


def test_root_defaults_to_none(spies: dict[str, MagicMock]) -> None:
    cli.main(["check"])
    assert spies["cmd_check"].call_args.args[0].root is None


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["conductor", "init"], "init"),
        (["conductor", "show"], "show"),
        (["conductor", "done", "--task-id", "T-1"], "done"),
        (["conductor", "block", "--task-id", "T-1", "--reason", "r"], "block"),
        (["conductor", "next"], "next"),
    ],
)
def test_conductor_subcommand_attribute(
    spies: dict[str, MagicMock], argv: list[str], expected: str
) -> None:
    cli.main(argv)
    assert spies["cmd_conductor"].call_args.args[0].conductor_command == expected


def test_parsed_options_reach_handler(spies: dict[str, MagicMock]) -> None:
    cli.main(["check", "--score", "--format", "github"])
    args = spies["cmd_check"].call_args.args[0]
    assert args.score is True
    assert args.format == "github"


def test_no_command_exits_with_usage_error() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main([])
    assert exc_info.value.code == 2

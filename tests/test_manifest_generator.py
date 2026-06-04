"""Tests for capability manifest generator."""

from pathlib import Path

from drifter.manifest_generator import (
    _scan_checks,
    _scan_cli_commands,
    _scan_mcp_tools,
    _scan_reporters,
    describe_json,
    describe_markdown,
    generate_manifest,
    write_manifest,
)


class TestScanCliCommands:
    def test_finds_top_level_commands(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        cli = src / "cli.py"
        cli.write_text(
            'subparsers.add_parser("check", help="Run drift guard")\n'
            'subparsers.add_parser("init", help="Initialize")\n'
        )
        cmds = _scan_cli_commands(tmp_path)
        names = {c.name for c in cmds}
        assert "check" in names
        assert "init" in names

    def test_finds_conductor_subcommands(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        cli = src / "cli.py"
        cli.write_text(
            'subparsers.add_parser("conductor")\n'
            'conductor_sub.add_parser("show", help="Show task")\n'
        )
        cmds = _scan_cli_commands(tmp_path)
        names = {c.name for c in cmds}
        assert "conductor" in names
        assert "conductor show" in names


class TestScanChecks:
    def test_reads_builtin_checks(self, tmp_path: Path) -> None:
        checks = tmp_path / "src" / "drifter" / "checks"
        checks.mkdir(parents=True)
        init = checks / "__init__.py"
        init.write_text(
            "BUILTIN_CHECKS: dict[str, type[Check]] = {\n"
            '    "stale_reference": StaleReferenceCheck,\n'
            '    "git_safety": GitSafetyCheck,\n'
            "}\n"
        )
        result = _scan_checks(tmp_path)
        names = {c.name for c in result}
        assert "stale_reference" in names
        assert "git_safety" in names


class TestScanMcpTools:
    def test_finds_mcp_tool_decorated_functions(self, tmp_path: Path) -> None:
        mcp = tmp_path / "plugins" / "mcp-server"
        mcp.mkdir(parents=True)
        server = mcp / "server.py"
        server.write_text(
            "@mcp.tool()\n"
            "def drifter_classify(command: str) -> str: ...\n"
            "@mcp_tool()\n"
            "def drifter_log(action: str) -> str: ...\n"
        )
        tools = _scan_mcp_tools(tmp_path)
        names = {t.name for t in tools}
        assert "drifter_classify" in names
        assert "drifter_log" in names


class TestScanReporters:
    def test_finds_reporter_modules(self, tmp_path: Path) -> None:
        reps = tmp_path / "src" / "drifter" / "reporters"
        reps.mkdir(parents=True)
        (reps / "__init__.py").write_text("")
        (reps / "console.py").write_text("class ConsoleReporter: ...\n")
        (reps / "json_reporter.py").write_text("class JsonReporter: ...\n")
        result = _scan_reporters(tmp_path)
        names = {r.name for r in result}
        assert "ConsoleReporter" in names
        assert "JsonReporter" in names


class TestGenerateManifest:
    def test_manifest_has_version(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "1.0.0"\n')
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        (src / "cli.py").write_text('subparsers.add_parser("check")\n')
        checks = src / "checks"
        checks.mkdir()
        (checks / "__init__.py").write_text("BUILTIN_CHECKS = {}\n")
        mcp = tmp_path / "plugins" / "mcp-server"
        mcp.mkdir(parents=True)
        (mcp / "server.py").write_text("")
        reps = src / "reporters"
        reps.mkdir()
        (reps / "__init__.py").write_text("")

        manifest = generate_manifest(tmp_path)
        assert manifest.version == "1.0.0"
        assert any(c.name == "check" for c in manifest.commands)


class TestWriteManifest:
    def test_writes_json_file(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "0.1.0"\n')
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        (src / "cli.py").write_text('subparsers.add_parser("check")\n')
        checks = src / "checks"
        checks.mkdir()
        (checks / "__init__.py").write_text("BUILTIN_CHECKS = {}\n")
        mcp = tmp_path / "plugins" / "mcp-server"
        mcp.mkdir(parents=True)
        (mcp / "server.py").write_text("")
        reps = src / "reporters"
        reps.mkdir()
        (reps / "__init__.py").write_text("")

        path = write_manifest(tmp_path)
        assert path.exists()
        data = path.read_text()
        assert '"version": "0.1.0"' in data


class TestDescribeFormats:
    def test_describe_json_is_valid(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "0.1.0"\n')
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        (src / "cli.py").write_text('subparsers.add_parser("check")\n')
        checks = src / "checks"
        checks.mkdir()
        (checks / "__init__.py").write_text("BUILTIN_CHECKS = {}\n")
        mcp = tmp_path / "plugins" / "mcp-server"
        mcp.mkdir(parents=True)
        (mcp / "server.py").write_text("")
        reps = src / "reporters"
        reps.mkdir()
        (reps / "__init__.py").write_text("")

        json_text = describe_json(tmp_path)
        assert '"version": "0.1.0"' in json_text
        assert '"commands"' in json_text

    def test_describe_markdown_contains_sections(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "0.1.0"\n')
        src = tmp_path / "src" / "drifter"
        src.mkdir(parents=True)
        (src / "cli.py").write_text('subparsers.add_parser("check")\n')
        checks = src / "checks"
        checks.mkdir()
        (checks / "__init__.py").write_text("BUILTIN_CHECKS = {}\n")
        mcp = tmp_path / "plugins" / "mcp-server"
        mcp.mkdir(parents=True)
        (mcp / "server.py").write_text("")
        reps = src / "reporters"
        reps.mkdir()
        (reps / "__init__.py").write_text("")

        md = describe_markdown(tmp_path)
        assert "# Drifter 0.1.0 — Capability Overview" in md
        assert "## CLI Commands" in md

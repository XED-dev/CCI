"""Smoke-Tests für xed-cci CLI-Skelett (SS1)."""

from __future__ import annotations

from typer.testing import CliRunner

from cci import __version__
from cci.cli import app

runner = CliRunner()


def test_version_flag_shows_version() -> None:
    """`cci --version` zeigt aktuelle Version + exit 0."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_shows_inventory_command() -> None:
    """`cci --help` listet das inventory-Verb."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "inventory" in result.stdout


def test_inventory_command_runs_default() -> None:
    """`cci inventory` läuft mit Default-Format (Rich) + Default-Section (all)."""
    result = runner.invoke(app, ["inventory"])
    assert result.exit_code == 0
    # Rich-Tabellen enthalten Sektion-Titel
    assert "OS" in result.stdout
    assert "CC-Suite" in result.stdout
    assert "Stack" in result.stdout

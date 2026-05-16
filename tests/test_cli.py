"""Smoke-Tests für xed-cci CLI-Skelett (SS1 + v0.0.9-Verb-Switch)."""

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


def test_help_shows_typo3_command() -> None:
    """`cci --help` listet das typo3-Verb (Box-Klassen-Subkommando v0.0.9)."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "typo3" in result.stdout


def test_typo3_command_runs_default() -> None:
    """`cci typo3` läuft mit Default-Format (Rich) + Default-Section (all)."""
    result = runner.invoke(app, ["typo3"])
    assert result.exit_code == 0
    # Rich-Tabellen enthalten Sektion-Titel
    assert "OS" in result.stdout
    assert "CC-Suite" in result.stdout
    assert "Stack" in result.stdout


def test_version_short_v_alias_shows_version() -> None:
    """v0.0.7: -v als Short-Form fuer --version (SysOps-Erwartung: -V belegt = -v belegt)."""
    result = runner.invoke(app, ["-v"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_short_h_alias_shows_help() -> None:
    """v0.0.7: -h als Short-Form fuer --help via Typer context_settings.

    v0.0.9: Help-Output zeigt typo3-Verb + Box-Klassen-Übersicht.
    """
    result = runner.invoke(app, ["-h"])
    assert result.exit_code == 0
    assert "typo3" in result.stdout


def test_help_shows_box_classes_overview() -> None:
    """v0.0.9: `cci --help` zeigt Box-Klassen-Übersicht + Beispiele.

    Top-Level-Help-Block ist substantiell erweitert (Senior-Hint G):
    Box-Klassen-Liste mit Kurzbeschreibung + Beispiel-Subkommandos.
    """
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Box-Klassen" in result.stdout
    assert "WordOps-LEMP" in result.stdout


def test_typo3_section_sites_runs() -> None:
    """v0.0.9: `cci typo3 --section sites` läuft (vormals `--section apps`)."""
    result = runner.invoke(app, ["typo3", "--section", "sites"])
    assert result.exit_code == 0
    # Sites-Sektion enthält Tabellen-Titel
    assert "Sites" in result.stdout

"""xed-cci CLI — Box-Klassen-Inventur-Tool (Typer-basiert).

v0.0.9 — Architektur-Pivot auf eingegrenzte Box-Klassen:
- `cci typo3` ersetzt `cci inventory` (Verb-basiert nach Box-Klasse)
- Aktuell unterstützte Box-Klasse: typo3 (WordOps-LEMP-Ubuntu-LTS +
  TYPO3-Composer + optional Solr-ADD-ON)
- Perspektivisch: weitere Box-Klassen (`cci wordpress`, ...) als
  eigene Top-Level-Verben

Designprinzipien (siehe WHITEPAPER §Vision + §Mission Statement):
- 100% Read-Only: cci verändert NIEMALS den Box-Zustand
- Stack-Konsistenz mit ccc + cca (Typer + Rich + pytest + pipx)
- AI-Agent-Konsumtion via JSON-Output (Schema 0.0.2 — Top-Level-Key
  `sites` statt vormals `apps`, BREAKING-Change v0.0.9)

Phase 2 (DeltaChat-Bot) + Phase 3 (cBOX@ /Monitor) sind Vision/Mission,
NICHT in Phase 1 umgesetzt.
"""

from __future__ import annotations

import sys
from typing import Optional

import typer
from rich.console import Console

from cci._version import __version__
from cci.commands.inventory import inventory_command

app = typer.Typer(
    name="cci",
    help=(
        "cBOX@ /Container Inventur — Read-Only-Tool für Box-Klassen-Inventur.\n\n"
        "Box-Klassen (verb-basierte Subkommandos):\n"
        "  typo3   WordOps-LEMP-Ubuntu-LTS + TYPO3-Composer + ADD-ONs (z.B. Apache Solr)\n\n"
        "Beispiele:\n"
        "  cci typo3                                  Komplette Box-Inventur (Rich)\n"
        "  cci typo3 --format json                    JSON für AI-Agent-Konsumtion\n"
        "  cci typo3 --section sites                  Nur TYPO3-Sites pro Domain\n"
        "  cci typo3 --section os                     Nur OS-Sektion\n"
        "  cci typo3 --format oneliner                1-Zeile copy-paste\n"
        "  cci typo3 --format text -o /tmp/inv.txt    Multi-line in Datei schreiben\n\n"
        "100% Read-Only: cci verändert NIEMALS den Box-Zustand.\n\n"
        "cBOX.at/YOU by XED.dev Tools via Collective Context (CC)."
    ),
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"xed-cci [bold]v{__version__}[/bold]")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Zeige Version und beende.",
        callback=version_callback,
        is_eager=True,
    ),
    dialog: Optional[bool] = typer.Option(
        None,
        "--dialog",
        "-d",
        help="Power-Dialog mit Verb-spezifischen Detail-Optionen (TBD — Platzhalter v0.0.7).",
        hidden=True,
    ),
) -> None:
    """xed-cci Top-Level-Callback. Lädt globale Optionen wie --version."""


# Box-Klassen-Verb `typo3` — WordOps-LEMP-Ubuntu-LTS + TYPO3-Composer + optional Solr.
# v0.0.9-Architektur-Pivot: Verb-basiert nach Box-Klasse statt generischem
# `inventory`-Verb. Weitere Box-Klassen (`cci wordpress`, ...) als künftige
# Top-Level-Verben analog.
app.command("typo3")(inventory_command)


def main() -> None:
    """Entry point für das `cci`-Script (siehe pyproject.toml [project.scripts])."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[red]Abgebrochen.[/red]")
        sys.exit(130)


if __name__ == "__main__":
    main()

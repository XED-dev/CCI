"""xed-cci CLI — Typer-basiertes Read-Only-Inventur-Tool.

Designprinzipien (siehe WHITEPAPER §Vision + §Mission Statement):
- 100% Read-Only: cci verändert NIEMALS den Box-Zustand
- Stack-Konsistenz mit ccc + cca (Typer + Rich + pytest + pipx)
- AI-Agent-Konsumtion via JSON-Output

Phase-1-Verben (v0.0.1+):
- inventory: komplette Box-Inventur (Rich-Tabelle oder JSON)

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
    help="cBOX@ /Container Inventur — Read-Only-Tool für lokale Box-Inventur.\n\n"
    "Liefert OS, CC-Suite-Versionen, Stacks, Datenbanken und Server-Apps\n"
    "als Rich-Tabelle (Mensch) oder JSON (AI-Agent-Konsumtion).\n\n"
    "100% Read-Only: cci verändert NIEMALS den Box-Zustand.\n\n"
    "cBOX.at/YOU by XED.dev Tools via Collective Context (CC).",
    no_args_is_help=True,
    add_completion=False,
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
        "-V",
        help="Zeige Version und beende.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """xed-cci Top-Level-Callback. Lädt globale Optionen wie --version."""


# inventory-Verb (SS5: Composition + Rich + JSON-Output + --section-Filter)
app.command("inventory")(inventory_command)


def main() -> None:
    """Entry point für das `cci`-Script (siehe pyproject.toml [project.scripts])."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[red]Abgebrochen.[/red]")
        sys.exit(130)


if __name__ == "__main__":
    main()

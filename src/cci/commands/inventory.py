"""inventory — cci inventory-Verb (Composition + Rich + JSON + --section).

Composition über die fünf Inventur-Sektionen (os/cc-suite/stack/databases/
apps). Output entweder Rich-Tabelle (Mensch) oder JSON (AI-Agent-Konsumtion).

Senior-Pre-Hints H6-H11 (AI039 SS5 2026-05-08):
- H6: InventoryReport TypedDict matcht WHITEPAPER §JSON-Schema 1:1
- H7: Rich für Mensch / json.dumps für AI-Agent
- H8: --section-Filter mit enum-Choices (os/cc-suite/stack/databases/apps/all)
- H9: datetime.now(timezone.utc).isoformat — KEIN deprecated utcnow()
- H10: socket.gethostname() — KEIN subprocess hostname
- H11: _SCHEMA_VERSION als Konstante (Single-Source-of-Truth)

Stdlib-Reflex maximiert: keine subprocess-Aufrufe in dieser Datei
(Composition + Output-Rendering nur).
"""

from __future__ import annotations

import json
import socket
from datetime import datetime, timezone
from enum import Enum
from typing import TypedDict

import typer
from rich.console import Console
from rich.table import Table

from cci.system.inventory.apps import AppInfo, collect_apps_info
from cci.system.inventory.cc_suite import CCSuiteInfo, collect_cc_suite_info
from cci.system.inventory.databases import DatabaseInfo, collect_databases_info
from cci.system.inventory.os import OSInfo, collect_os_info
from cci.system.inventory.stack import StackInfo, collect_stack_info

_SCHEMA_VERSION = "0.0.1"


class InventoryReport(TypedDict):
    """Vollständige Inventur-Composition matching WHITEPAPER §JSON-Schema."""

    schema_version: str
    timestamp: str
    host: str
    os: OSInfo
    cc_suite: CCSuiteInfo
    stack: StackInfo
    databases: list[DatabaseInfo]
    apps: list[AppInfo]


class Section(str, Enum):
    """Erlaubte --section-Werte (Typer-Choices)."""

    ALL = "all"
    OS = "os"
    CC_SUITE = "cc-suite"
    STACK = "stack"
    DATABASES = "databases"
    APPS = "apps"


def _utc_timestamp() -> str:
    """ISO-UTC-Zeitstempel mit 'Z'-Suffix (kompatibel zu audit_log-Format)."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _build_report() -> InventoryReport:
    """Baue komplette InventoryReport via Composition aller collect_X_info()."""
    return InventoryReport(
        schema_version=_SCHEMA_VERSION,
        timestamp=_utc_timestamp(),
        host=socket.gethostname(),
        os=collect_os_info(),
        cc_suite=collect_cc_suite_info(),
        stack=collect_stack_info(),
        databases=collect_databases_info(),
        apps=collect_apps_info(),
    )


def _filter_report(report: InventoryReport, section: Section) -> dict:
    """Filtere Report auf gewählte Sektion (alle wenn Section.ALL).

    Returns dict statt InventoryReport weil bei Section-Filter die
    TypedDict-Struktur verändert wird (nur Subkey).
    """
    if section is Section.ALL:
        return dict(report)

    # Schema-Header bleibt immer drin für Kontext, plus die gewählte Sektion
    base = {
        "schema_version": report["schema_version"],
        "timestamp": report["timestamp"],
        "host": report["host"],
    }
    section_key = section.value.replace("-", "_")  # 'cc-suite' -> 'cc_suite'
    base[section_key] = report[section_key]  # type: ignore[literal-required]
    return base


def _render_rich(console: Console, report: InventoryReport, section: Section) -> None:
    """Rich-Tabellen-Output für gewählte Sektion(en)."""
    if section in (Section.ALL, Section.OS):
        _render_os(console, report["os"])
    if section in (Section.ALL, Section.CC_SUITE):
        _render_cc_suite(console, report["cc_suite"])
    if section in (Section.ALL, Section.STACK):
        _render_stack(console, report["stack"])
    if section in (Section.ALL, Section.DATABASES):
        _render_databases(console, report["databases"])
    if section in (Section.ALL, Section.APPS):
        _render_apps(console, report["apps"])

    if section is Section.ALL:
        console.print(
            f"[dim]Schema {report['schema_version']} · "
            f"{report['timestamp']} · {report['host']}[/dim]"
        )


def _render_os(console: Console, os_info: OSInfo) -> None:
    table = Table(title="OS", show_header=True, header_style="bold cyan")
    table.add_column("Field")
    table.add_column("Value")
    for key in ("id", "version_id", "pretty_name", "kernel"):
        table.add_row(key, os_info[key])  # type: ignore[literal-required]
    console.print(table)


def _render_cc_suite(console: Console, cc: CCSuiteInfo) -> None:
    table = Table(title="CC-Suite", show_header=True, header_style="bold cyan")
    table.add_column("Tool")
    table.add_column("Version")
    for tool in ("xed-ccc", "xed-cca", "xed-cci"):
        table.add_row(tool, cc[tool])  # type: ignore[literal-required]
    console.print(table)


def _render_stack(console: Console, stack: StackInfo) -> None:
    table = Table(title="Stack", show_header=True, header_style="bold cyan")
    table.add_column("Language")
    table.add_column("Version")
    table.add_row("python3", stack["python3"])
    table.add_row("php", stack["php"] or "[dim]not installed[/dim]")
    table.add_row("node", stack["node"] or "[dim]not installed[/dim]")
    console.print(table)


def _render_databases(console: Console, dbs: list[DatabaseInfo]) -> None:
    table = Table(title="Databases", show_header=True, header_style="bold cyan")
    table.add_column("Engine")
    table.add_column("Version")
    table.add_column("Service Active", justify="center")
    if not dbs:
        table.add_row("[dim](none)[/dim]", "", "")
    for db in dbs:
        active = "[green]✓[/green]" if db["service_active"] else "[red]✗[/red]"
        table.add_row(db["engine"], db["version"], active)
    console.print(table)


def _render_apps(console: Console, apps: list[AppInfo]) -> None:
    table = Table(title="Server-Apps", show_header=True, header_style="bold cyan")
    table.add_column("Name")
    table.add_column("Version")
    table.add_column("Path")
    if not apps:
        table.add_row("[dim](none)[/dim]", "", "")
    for app in apps:
        table.add_row(app["name"], app["version"], app["path"])
    console.print(table)


def inventory_command(
    section: Section = typer.Option(
        Section.ALL,
        "--section",
        case_sensitive=False,
        help="Welche Sektion ausgeben (Default: alle).",
    ),
    output_format: str = typer.Option(
        "rich",
        "--format",
        case_sensitive=False,
        help="Output-Format: 'rich' (Tabellen für Mensch) oder 'json' (AI-Agent).",
    ),
) -> None:
    """Box-Inventur als Rich-Tabelle oder JSON.

    Sektionen: os, cc-suite, stack, databases, apps, all (Default).

    Beispiele:
        cci inventory
        cci inventory --section os
        cci inventory --format json > /tmp/box.json
    """
    report = _build_report()

    fmt = output_format.lower()
    if fmt == "json":
        # JSON-Output via stdout, Rich-Console-Output deaktiviert um
        # Format-Kontamination zu vermeiden (Senior-Pre-Hint H7/H8 STOPP-
        # Kriterium: bei --format json darf KEIN Rich-Output dazwischen
        # rutschen).
        filtered = _filter_report(report, section)
        print(json.dumps(filtered, indent=2))
        return

    if fmt == "rich":
        console = Console()
        _render_rich(console, report, section)
        return

    raise typer.BadParameter(
        f"Unbekanntes Format: {output_format!r}. Erlaubt: 'rich' oder 'json'."
    )

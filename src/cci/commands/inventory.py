"""inventory — Box-Klassen-Inventur-Implementation für cci typo3.

Composition über die fünf Inventur-Sektionen (os/cc-suite/stack/databases/
sites). Output entweder Rich-Tabelle (Mensch) oder JSON (AI-Agent-
Konsumtion). CLI-Verb seit v0.0.9: `cci typo3` (vormals `cci inventory`,
Architektur-Pivot auf Box-Klassen-Subkommandos — siehe `cli.py`).

Pattern-Anker für Composition:
- InventoryReport TypedDict matcht WHITEPAPER §JSON-Schema 1:1
- Rich für Mensch / json.dumps für AI-Agent
- --section-Filter mit enum-Choices (os/cc-suite/stack/databases/sites/all)
- datetime.now(timezone.utc).isoformat — KEIN deprecated utcnow()
- socket.gethostname() — KEIN subprocess hostname
- _SCHEMA_VERSION als Konstante (Single-Source-of-Truth)

v0.0.9-Schema-Bump 0.0.1 → 0.0.2:
- Top-Level-Key `apps` → `sites` (Output-Aggregations-Layer-Konvention)
- Detector-Layer-Code (`system/inventory/apps/*` + AppInfo) bleibt
  unverändert — Section-Naming folgt Box-Klassen-Output-Domain,
  Detector-Naming folgt Implementation-Domain.

Stdlib-Reflex maximiert: keine subprocess-Aufrufe in dieser Datei
(Composition + Output-Rendering nur).
"""

from __future__ import annotations

import json
import socket
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, TypedDict

import typer
from rich.console import Console
from rich.table import Table

from cci.system.inventory.apps import AppInfo, collect_apps_info
from cci.system.inventory.cc_suite import CCSuiteInfo, collect_cc_suite_info
from cci.system.inventory.databases import DatabaseInfo, collect_databases_info
from cci.system.inventory.os import OSInfo, collect_os_info
from cci.system.inventory.stack import StackInfo, collect_stack_info

_SCHEMA_VERSION = "0.0.2"


class InventoryReport(TypedDict):
    """Vollständige Inventur-Composition matching WHITEPAPER §JSON-Schema.

    v0.0.9: Top-Level-Key `apps` → `sites` (BREAKING — siehe Schema-Bump
    0.0.1 → 0.0.2). Inhalt unverändert — Liste von AppInfo-Records,
    aber unter neuem Aggregations-Layer-Namen.
    """

    schema_version: str
    timestamp: str
    host: str
    os: OSInfo
    cc_suite: CCSuiteInfo
    stack: StackInfo
    databases: list[DatabaseInfo]
    sites: list[AppInfo]


class Section(str, Enum):
    """Erlaubte --section-Werte (Typer-Choices).

    v0.0.9: `APPS = "apps"` → `SITES = "sites"` (Box-Klassen-Aggregations-
    Layer-Naming).
    """

    ALL = "all"
    OS = "os"
    CC_SUITE = "cc-suite"
    STACK = "stack"
    DATABASES = "databases"
    SITES = "sites"


def _utc_timestamp() -> str:
    """ISO-UTC-Zeitstempel mit 'Z'-Suffix (kompatibel zu audit_log-Format)."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _build_report() -> InventoryReport:
    """Baue komplette InventoryReport via Composition aller collect_X_info().

    Detector-Layer-Helper `collect_apps_info()` liefert weiterhin
    `list[AppInfo]` — wird hier unter `sites`-Key gebündelt (Section-
    Output-Konvention, Detector-Naming bleibt für Implementation-Klarheit).
    """
    return InventoryReport(
        schema_version=_SCHEMA_VERSION,
        timestamp=_utc_timestamp(),
        host=socket.gethostname(),
        os=collect_os_info(),
        cc_suite=collect_cc_suite_info(),
        stack=collect_stack_info(),
        databases=collect_databases_info(),
        sites=collect_apps_info(),
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
    if section in (Section.ALL, Section.SITES):
        _render_sites(console, report["sites"])

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


def _render_sites(console: Console, sites: list[AppInfo]) -> None:
    """Render Sites-Sektion (TYPO3-Site-Layer pro Domain).

    v0.0.9: vormals `_render_apps()` — umbenannt zu Section-Aggregations-
    Naming. Datenstruktur (`AppInfo` aus Detector-Layer) bleibt unverändert.
    """
    table = Table(title="Sites", show_header=True, header_style="bold cyan")
    table.add_column("Name")
    table.add_column("Version")
    table.add_column("Path")
    if not sites:
        table.add_row("[dim](none)[/dim]", "", "")
    for site in sites:
        table.add_row(site["name"], site["version"], site["path"])
    console.print(table)


def _render_oneliner(report: InventoryReport, section: Section) -> str:
    """Pipe-separated One-Liner, copy-paste-friendly für Chat-Sharing.

    Format: section1:items|section2:items|... mit Items per Section
    Comma-separated. Header (schema/host/timestamp) immer drin für Kontext.

    Beispiel-Output (alle Sektionen):
        schema:0.0.2|host:osU2404|timestamp:...|os:Ubuntu-22.04.5-LTS|
        kernel:5.4.203-1-pve|cc-suite:ccc-0.2.3,cca-0.0.5,cci-0.0.9|
        stack:py-3.10.12,php-8.4.21|databases:mariadb-10.6.23(active)|
        sites:typo3-13.4.1@/var/www/site/(composer.json,composer-mode)
    """
    parts: list[str] = [
        f"schema:{report['schema_version']}",
        f"host:{report['host']}",
        f"timestamp:{report['timestamp']}",
    ]

    if section in (Section.ALL, Section.OS):
        os_info = report["os"]
        parts.append(f"os:{os_info['pretty_name'].replace(' ', '-')}")
        parts.append(f"kernel:{os_info['kernel']}")

    if section in (Section.ALL, Section.CC_SUITE):
        cc = report["cc_suite"]
        cc_parts = [
            f"{tool.replace('xed-', '')}-{cc[tool]}"  # type: ignore[literal-required]
            for tool in ("xed-ccc", "xed-cca", "xed-cci")
        ]
        parts.append(f"cc-suite:{','.join(cc_parts)}")

    if section in (Section.ALL, Section.STACK):
        stack = report["stack"]
        items: list[str] = []
        if stack["python3"]:
            items.append(f"py-{stack['python3']}")
        if stack["php"]:
            items.append(f"php-{stack['php']}")
        if stack["node"]:
            items.append(f"node-{stack['node']}")
        parts.append(f"stack:{','.join(items) if items else '(none)'}")

    if section in (Section.ALL, Section.DATABASES):
        if report["databases"]:
            db_items = [
                f"{db['engine']}-{db['version']}"
                f"({'active' if db['service_active'] else 'inactive'})"
                for db in report["databases"]
            ]
            parts.append(f"databases:{','.join(db_items)}")
        else:
            parts.append("databases:(none)")

    if section in (Section.ALL, Section.SITES):
        if report["sites"]:
            site_items = [
                f"{site['name']}-{site['version']}@{site['path']}"
                f"({site['config_file']},{site['mode']}-mode)"
                for site in report["sites"]
            ]
            parts.append(f"sites:{','.join(site_items)}")
        else:
            parts.append("sites:(none)")

    return "|".join(parts)


def _render_text(report: InventoryReport, section: Section) -> str:
    """Plain multi-line Text (kein Rich-Markup) für File-Output + cat.

    Sektional mit [Section]-Headern und key=value-Lines (INI-artig).
    Geeignet für `cci typo3 --format text --output inv.txt` + `cat inv.txt`.
    """
    lines: list[str] = [
        f"# cci inventory — schema {report['schema_version']}",
        f"# host: {report['host']}",
        f"# timestamp: {report['timestamp']}",
        "",
    ]

    if section in (Section.ALL, Section.OS):
        os_info = report["os"]
        lines.append("[OS]")
        for key in ("id", "version_id", "pretty_name", "kernel"):
            lines.append(f"  {key} = {os_info[key]}")  # type: ignore[literal-required]
        lines.append("")

    if section in (Section.ALL, Section.CC_SUITE):
        cc = report["cc_suite"]
        lines.append("[CC-Suite]")
        for tool in ("xed-ccc", "xed-cca", "xed-cci"):
            lines.append(f"  {tool} = {cc[tool]}")  # type: ignore[literal-required]
        lines.append("")

    if section in (Section.ALL, Section.STACK):
        stack = report["stack"]
        lines.append("[Stack]")
        lines.append(f"  python3 = {stack['python3']}")
        lines.append(f"  php = {stack['php'] or '(not installed)'}")
        lines.append(f"  node = {stack['node'] or '(not installed)'}")
        lines.append("")

    if section in (Section.ALL, Section.DATABASES):
        lines.append("[Databases]")
        if not report["databases"]:
            lines.append("  (none)")
        for db in report["databases"]:
            active = "active" if db["service_active"] else "inactive"
            lines.append(f"  {db['engine']} = {db['version']} ({active})")
        lines.append("")

    if section in (Section.ALL, Section.SITES):
        lines.append("[Sites]")
        if not report["sites"]:
            lines.append("  (none)")
        for site in report["sites"]:
            lines.append(f"  {site['name']} {site['version']}")
            lines.append(f"    path   = {site['path']}")
            lines.append(f"    config = {site['config_file']}")
            lines.append(f"    mode   = {site['mode']}")
        lines.append("")

    return "\n".join(lines)


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
        help="Format: rich (Tabellen) | json (AI-Agent) | oneliner (Single-Line) | text (Plain)",
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output in Datei statt stdout (alle Formate). Beispiel: --output /tmp/inventory.txt",
    ),
) -> None:
    """Box-Inventur als Rich-Tabelle, JSON, One-Liner oder Plain-Text.

    Sektionen: os, cc-suite, stack, databases, sites, all (Default).

    Formate (v0.0.8 + v0.0.9):

        rich     — Rich-Tabellen für Mensch (Default)
        json     — AI-Agent-Konsumtion (Indent 2)
        oneliner — Single-Line pipe-separated, copy-paste-friendly für Chat
        text     — Plain multi-line (kein Rich-Markup), File-Output + cat

    Beispiele:

        cci typo3                                # Komplette Inventur (Rich)
        cci typo3 --format json                  # JSON für AI-Agent
        cci typo3 --section os                   # Nur OS-Sektion
        cci typo3 --section sites                # Nur TYPO3-Sites
        cci typo3 --format oneliner              # 1-Zeile copy-paste
        cci typo3 --format text -o /tmp/inv.txt  # In Datei schreiben
    """
    report = _build_report()
    fmt = output_format.lower()

    # Rich-Format: Console.print direkt zu stdout oder file
    if fmt == "rich":
        if output_file is not None:
            with output_file.open("w", encoding="utf-8") as fp:
                console = Console(file=fp, force_terminal=False, width=120)
                _render_rich(console, report, section)
        else:
            _render_rich(Console(), report, section)
        return

    # Non-Rich-Formate: String-Builder, dann zu stdout oder file
    if fmt == "json":
        # JSON-Output: bei Section-Filter nur die gewählte Sektion ausgeben
        # (statt gesamten Report), für AI-Agent-Konsumtion-Klarheit.
        filtered = _filter_report(report, section)
        content = json.dumps(filtered, indent=2)
    elif fmt == "oneliner":
        content = _render_oneliner(report, section)
    elif fmt == "text":
        content = _render_text(report, section)
    else:
        raise typer.BadParameter(
            f"Unbekanntes Format: {output_format!r}. "
            "Erlaubt: 'rich' | 'json' | 'oneliner' | 'text'."
        )

    if output_file is not None:
        output_file.write_text(content + "\n", encoding="utf-8")
    else:
        print(content)

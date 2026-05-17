"""inventory — Box-Klassen-Inventur-Implementation für cci typo3.

Composition über die fünf Inventur-Sektionen (os/cc-suite/stack/databases/
sites). Output entweder Rich-Tabelle (Mensch) oder JSON (AI-Agent-
Konsumtion). CLI-Verb seit v0.0.9: `cci typo3`.

Pattern-Anker für Composition:
- InventoryReport TypedDict matcht WHITEPAPER §JSON-Schema 1:1
- Rich für Mensch / json.dumps für AI-Agent
- --section-Filter mit enum-Choices (os/cc-suite/stack/databases/sites/all)
- datetime.now(timezone.utc).isoformat — KEIN deprecated utcnow()
- socket.gethostname() — KEIN subprocess hostname
- _SCHEMA_VERSION als Konstante (Single-Source-of-Truth)

v0.0.10-Schema-Bump 0.0.2 → 0.0.3 (BREAKING):
- Site-Item-Schema neu: SiteEntry (Webroot-zentriert) + nested DomainInfo
  (DevOps-Vote 2026-05-17: „Webroot ist Quelle der Wahrheit, Domain ist
  View darauf"). Multi-Webroot-Mapping (mehrere Domains teilen Webroot
  mit unterschiedlichen PHP-Versionen) wird natürlich erfasst.
- Detection-Wurzel-Fix: collect_sites_info() (sites.py) via Werkzeug-
  First (`wo site list` + Nginx-Config-Parse + Multi-Source-Detection)
  ersetzt legacy `/var/www/`-iterdir-Heuristik aus collect_apps_info().
- Box-Klassen-Pre-Step (box_class.py) als Hard-Gate vor Inventur:
  Ubuntu LTS 22.04/24.04 + WordOps-CLI + nginx-wo-Build. Bei Mismatch
  Exit 2 mit klarer Meldung.

Stdlib-Reflex maximiert: keine subprocess-Aufrufe in dieser Datei
(Composition + Output-Rendering nur). Subprocess-Aufrufe (`wo site list`,
`dpkg-query`) sind in sites.py + box_class.py + collect_*-Helpers
gekapselt mit safe_run-Whitelist.
"""

from __future__ import annotations

import json
import socket
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, TypedDict

import typer
from rich.console import Console
from rich.table import Table

from cci.system.inventory.box_class import verify_typo3_box_class
from cci.system.inventory.cc_suite import CCSuiteInfo, collect_cc_suite_info
from cci.system.inventory.databases import DatabaseInfo, collect_databases_info
from cci.system.inventory.os import OSInfo, collect_os_info
from cci.system.inventory.sites import SiteEntry, collect_sites_info
from cci.system.inventory.stack import StackInfo, collect_stack_info

_SCHEMA_VERSION = "0.0.3"


class InventoryReport(TypedDict):
    """Vollständige Inventur-Composition matching WHITEPAPER §JSON-Schema.

    v0.0.10: `sites` ist jetzt `list[SiteEntry]` (Webroot-zentriert mit
    nested DomainInfo), BREAKING-Change zu v0.0.9 (`list[AppInfo]`).
    """

    schema_version: str
    timestamp: str
    host: str
    os: OSInfo
    cc_suite: CCSuiteInfo
    stack: StackInfo
    databases: list[DatabaseInfo]
    sites: list[SiteEntry]


class Section(str, Enum):
    """Erlaubte --section-Werte (Typer-Choices)."""

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

    v0.0.10: `sites` via `collect_sites_info()` aus sites.py
    (Werkzeug-First Site-Enumeration + Multi-Source-Detection),
    NICHT mehr legacy `collect_apps_info()` aus apps/__init__.py.
    """
    return InventoryReport(
        schema_version=_SCHEMA_VERSION,
        timestamp=_utc_timestamp(),
        host=socket.gethostname(),
        os=collect_os_info(),
        cc_suite=collect_cc_suite_info(),
        stack=collect_stack_info(),
        databases=collect_databases_info(),
        sites=collect_sites_info(),
    )


def _filter_report(report: InventoryReport, section: Section) -> dict:
    """Filtere Report auf gewählte Sektion (alle wenn Section.ALL)."""
    if section is Section.ALL:
        return dict(report)

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


def _render_sites(console: Console, sites: list[SiteEntry]) -> None:
    """Render Sites-Sektion pro Webroot mit nested Domains (v0.0.10).

    Multi-Line pro Webroot mit Tree-Zeichen (├─ / └─) für Domain-Liste.
    DevOps-Vote: Webroot ist Quelle der Wahrheit, Domains+PHP als Attribute.
    """
    table = Table(title="Sites (per Webroot)", show_header=True, header_style="bold cyan")
    table.add_column("CMS")
    table.add_column("Version")
    table.add_column("Webroot + Domains")

    if not sites:
        table.add_row("[dim](none)[/dim]", "", "")
        console.print(table)
        return

    for site in sites:
        cms_cell = site["cms"] if site["cms"] != "unknown" else "[dim]?[/dim]"
        version_cell = (
            site["cms_version"]
            if site["cms_version"] not in ("unknown", "")
            else "[dim]?[/dim]"
        )

        # Build the Webroot+Domains nested cell
        lines = [site["webroot"]]
        domain_count = len(site["domains"])
        for i, domain_info in enumerate(site["domains"]):
            is_last = i == domain_count - 1
            tree_char = "└─" if is_last else "├─"
            lines.append(
                f"  {tree_char} {domain_info['domain']} (PHP {domain_info['php_version']})"
            )
        webroot_cell = "\n".join(lines)

        table.add_row(cms_cell, version_cell, webroot_cell)

    console.print(table)


def _render_oneliner(report: InventoryReport, section: Section) -> str:
    """Pipe-separated One-Liner, copy-paste-friendly für Chat-Sharing.

    v0.0.10: sites-Section ist pro Webroot mit comma-separated Domains.
    Beispiel:
        sites:typo3-12.4.45@/var/www/preprod.../public[
            preprod.scheucherparkett.com:7.4,scheucherparkett.at:8.3]
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
            site_items = []
            for site in report["sites"]:
                cms = site["cms"]
                version = site["cms_version"]
                webroot = site["webroot"]
                domain_strs = [
                    f"{d['domain']}:{d['php_version']}" for d in site["domains"]
                ]
                site_items.append(
                    f"{cms}-{version}@{webroot}[{','.join(domain_strs)}]"
                )
            parts.append(f"sites:{','.join(site_items)}")
        else:
            parts.append("sites:(none)")

    return "|".join(parts)


def _render_text(report: InventoryReport, section: Section) -> str:
    """Plain multi-line Text (kein Rich-Markup) für File-Output + cat.

    v0.0.10: sites-Section pro Webroot mit nested Domains-Block.
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
            lines.append(f"  {site['cms']} {site['cms_version']}")
            lines.append(f"    webroot      = {site['webroot']}")
            lines.append(f"    project_root = {site['project_root']}")
            lines.append(f"    cms_mode     = {site['cms_mode']}")
            if site["cms_source"]:
                lines.append(f"    cms_source   = {site['cms_source']}")
            if site["config_file"]:
                lines.append(f"    config_file  = {site['config_file']}")
            lines.append(f"    domains      = {len(site['domains'])}")
            for d in site["domains"]:
                lines.append(
                    f"      - {d['domain']} (PHP {d['php_version']})"
                )
        lines.append("")

    return "\n".join(lines)


def _box_class_pre_step() -> None:
    """Box-Klassen-Pre-Step (Sub-Sprint N, v0.0.10).

    Hard-Gate vor Inventur: wenn die Box keine WordOps-LEMP-Ubuntu-LTS-Box
    ist, schreibe Mismatch-Details nach stderr und beende mit Exit 2.

    Raises:
        typer.Exit: Code 2 bei Box-Klassen-Mismatch.
    """
    result = verify_typo3_box_class()
    if result.ok:
        return

    # Klare Mismatch-Meldung auf stderr (Box-Klassen-Pre-Step ist
    # Sicherheits-Hard-Gate, nicht inhaltliche Inventur).
    print(
        "cci typo3: Box-Klassen-Mismatch — diese Box ist keine "
        "WordOps-LEMP-Ubuntu-LTS-Box.",
        file=sys.stderr,
    )
    for err in result.errors:
        print(f"  - {err}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Live-Diagnostik:", file=sys.stderr)
    for key, val in result.diagnostics.items():
        print(f"  {key} = {val}", file=sys.stderr)
    raise typer.Exit(code=2)


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

    Formate:

        rich     — Rich-Tabellen für Mensch (Default)
        json     — AI-Agent-Konsumtion (Indent 2)
        oneliner — Single-Line pipe-separated, copy-paste-friendly für Chat
        text     — Plain multi-line (kein Rich-Markup), File-Output + cat

    Beispiele:

        cci typo3                                # Komplette Inventur (Rich)
        cci typo3 --format json                  # JSON für AI-Agent
        cci typo3 --section sites                # Nur TYPO3-Sites pro Webroot
        cci typo3 --format oneliner              # 1-Zeile copy-paste
        cci typo3 --format text -o /tmp/inv.txt  # In Datei schreiben

    v0.0.10: Pre-Step verifiziert Box-Klasse (Ubuntu LTS + WordOps + nginx-wo).
    Bei Mismatch: Exit 2 mit klarer Diagnostik auf stderr.
    """
    # Sub-Sprint N: Box-Klassen-Pre-Step. Bei Mismatch → typer.Exit(2).
    _box_class_pre_step()

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

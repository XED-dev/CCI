"""Tests für cci.commands.inventory — Composition + Rich + JSON + --section.

v0.0.9 — Schema 0.0.1 → 0.0.2 + Top-Level-Key `apps` → `sites` +
Verb-Switch `cci inventory` → `cci typo3`.
"""

from __future__ import annotations

import json
import re
from unittest.mock import patch

from typer.testing import CliRunner

from cci.cli import app
from cci.commands.inventory import (
    InventoryReport,
    Section,
    _build_report,
    _filter_report,
    _utc_timestamp,
)
from cci.system.inventory.box_class import BoxClassCheckResult

runner = CliRunner()


# Case 1: _utc_timestamp matcht ISO-UTC mit Z-Suffix (kompatibel zu audit_log)
def test_utc_timestamp_format() -> None:
    ts = _utc_timestamp()
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", ts), (
        f"Timestamp matcht nicht ISO-UTC mit Z-Suffix: {ts!r}"
    )


# Case 2: _build_report bündelt alle Sektionen + Schema-Header
def test_build_report_contains_all_sections() -> None:
    """Live-Run: _build_report ruft alle 5 collect_X_info() auf + bündelt."""
    report = _build_report()
    # Schema-Header (v0.0.9: 0.0.2 nach apps→sites-Bump)
    assert report["schema_version"] == "0.0.3"
    assert isinstance(report["timestamp"], str)
    assert isinstance(report["host"], str)
    # Alle 5 Sektionen vorhanden
    assert "id" in report["os"]
    assert "xed-ccc" in report["cc_suite"]
    assert "python3" in report["stack"]
    assert isinstance(report["databases"], list)
    assert isinstance(report["sites"], list)


# Case 3: --format json gibt valides JSON aus mit allen Sektionen
def test_inventory_format_json_full_report() -> None:
    result = runner.invoke(app, ["typo3", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["schema_version"] == "0.0.3"
    assert "os" in data
    assert "cc_suite" in data
    assert "stack" in data
    assert "databases" in data
    assert "sites" in data


# Case 4: --section os filtert auf einzelne Sektion (JSON)
def test_inventory_section_os_only_json() -> None:
    result = runner.invoke(app, ["typo3", "--section", "os", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "os" in data
    # Andere Sektionen sind NICHT im gefilterten Output
    assert "cc_suite" not in data
    assert "stack" not in data
    assert "databases" not in data
    assert "sites" not in data
    # Schema-Header bleibt für Kontext
    assert data["schema_version"] == "0.0.3"


# Case 5: --section cc-suite mit Bindestrich-Choice (Typer-Enum-Mapping)
def test_inventory_section_cc_suite_dash_choice() -> None:
    """Section 'cc-suite' (mit Bindestrich) → Filter auf cc_suite-Subkey."""
    result = runner.invoke(app, ["typo3", "--section", "cc-suite", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "cc_suite" in data
    assert "os" not in data


# Case 6: --section all (Default) gibt alle Sektionen aus
def test_inventory_section_all_includes_everything() -> None:
    result = runner.invoke(app, ["typo3", "--section", "all", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    for key in ("os", "cc_suite", "stack", "databases", "sites"):
        assert key in data


# Case 7: Ungültiges --format raised typer.BadParameter
def test_inventory_invalid_format_raises() -> None:
    result = runner.invoke(app, ["typo3", "--format", "xml"])
    assert result.exit_code != 0


# Case 8: WHITEPAPER-Schema-Match: alle erwarteten Top-Level-Keys + Werte-Typen
def test_inventory_json_matches_whitepaper_schema() -> None:
    """JSON-Output muss WHITEPAPER §JSON-Output-Schema 1:1 matchen.

    v0.0.9: Top-Level-Key `apps` → `sites` (Schema-Bump 0.0.1 → 0.0.2).
    """
    result = runner.invoke(app, ["typo3", "--format", "json"])
    data = json.loads(result.stdout)

    # Top-Level-Keys (v0.0.9: `sites` statt `apps`)
    expected_keys = {
        "schema_version", "timestamp", "host",
        "os", "cc_suite", "stack", "databases", "sites",
    }
    assert set(data.keys()) == expected_keys

    # OS-Sub-Keys
    assert set(data["os"].keys()) == {"id", "version_id", "pretty_name", "kernel"}

    # CC-Suite-Sub-Keys (Bindestriche!)
    assert set(data["cc_suite"].keys()) == {"xed-ccc", "xed-cca", "xed-cci"}

    # Stack-Sub-Keys
    assert set(data["stack"].keys()) == {"python3", "php", "node"}

    # databases ist Liste
    assert isinstance(data["databases"], list)

    # sites ist Liste (v0.0.9: vormals `apps`)
    assert isinstance(data["sites"], list)


# Case 9: _filter_report mit Section.OS gibt nur OS-Subkey + Header
def test_filter_report_os_only() -> None:
    """Unit-Test der _filter_report-Logik (separat von CLI-Invocation)."""
    report: InventoryReport = {
        "schema_version": "0.0.3",
        "timestamp": "2026-05-15T12:00:00Z",
        "host": "test-box",
        "os": {"id": "ubuntu", "version_id": "24.04",
               "pretty_name": "Ubuntu 24.04 LTS", "kernel": "6.8.0"},
        "cc_suite": {"xed-ccc": "0.2.3", "xed-cca": "0.0.5", "xed-cci": "0.0.9"},
        "stack": {"python3": "3.12.3", "php": None, "node": None},
        "databases": [],
        "sites": [],
    }
    filtered = _filter_report(report, Section.OS)
    assert "os" in filtered
    assert "cc_suite" not in filtered
    assert filtered["schema_version"] == "0.0.3"


# Case 10: _filter_report mit Section.ALL gibt vollständigen Report
def test_filter_report_all_returns_full_report() -> None:
    report: InventoryReport = {
        "schema_version": "0.0.3",
        "timestamp": "2026-05-15T12:00:00Z",
        "host": "test-box",
        "os": {"id": "ubuntu", "version_id": "24.04",
               "pretty_name": "Ubuntu 24.04 LTS", "kernel": "6.8.0"},
        "cc_suite": {"xed-ccc": "0.2.3", "xed-cca": "0.0.5", "xed-cci": "0.0.9"},
        "stack": {"python3": "3.12.3", "php": None, "node": None},
        "databases": [],
        "sites": [],
    }
    filtered = _filter_report(report, Section.ALL)
    assert set(filtered.keys()) == {
        "schema_version", "timestamp", "host",
        "os", "cc_suite", "stack", "databases", "sites",
    }


# ---------------------------------------------------------------------------
# v0.0.10 — Box-Klassen-Pre-Step Integration
# ---------------------------------------------------------------------------


# Case 11: cci typo3 exits_on_box_mismatch (Pre-Step Hard-Gate, Sub-Sprint N)
def test_inventory_command_exits_on_box_mismatch() -> None:
    """v0.0.10 Box-Klassen-Mismatch → Exit 2 + Diagnostik auf stderr.

    Note: dieser Test-Name enthält `exits_on_box_mismatch`, conftest.py
    skippt das autouse-Mock und wir setzen eigenes Mock mit ok=False.
    """
    mismatch_result = BoxClassCheckResult(
        ok=False,
        errors=[
            "Box ist 'debian' (erwartet: Ubuntu LTS 22.04 oder 24.04)",
            "WordOps-CLI `wo` nicht im PATH",
            "nginx-wo-Paket nicht installiert (dpkg-query: unbekannt)",
        ],
        diagnostics={
            "os": "debian 12",
            "wo_binary": "missing",
            "nginx_wo": "not-installed",
        },
    )

    with patch(
        "cci.commands.inventory.verify_typo3_box_class",
        return_value=mismatch_result,
    ):
        result = runner.invoke(app, ["typo3"])

    assert result.exit_code == 2
    # Mismatch-Banner + Errors landen auf stderr (vermischt mit stdout im
    # default CliRunner-Mode — "Box-Klassen-Mismatch" sollte irgendwo
    # im Output sein).
    combined = result.stdout + (result.stderr if result.stderr else "")
    assert "Box-Klassen-Mismatch" in combined
    assert "debian" in combined
    assert "nginx-wo" in combined

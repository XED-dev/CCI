"""Tests für cci.commands.inventory — Composition + Rich + JSON + --section."""

from __future__ import annotations

import json
import re

from typer.testing import CliRunner

from cci.cli import app
from cci.commands.inventory import (
    InventoryReport,
    Section,
    _build_report,
    _filter_report,
    _utc_timestamp,
)

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
    # Schema-Header
    assert report["schema_version"] == "0.0.1"
    assert isinstance(report["timestamp"], str)
    assert isinstance(report["host"], str)
    # Alle 5 Sektionen vorhanden
    assert "id" in report["os"]
    assert "xed-ccc" in report["cc_suite"]
    assert "python3" in report["stack"]
    assert isinstance(report["databases"], list)
    assert isinstance(report["apps"], list)


# Case 3: --format json gibt valides JSON aus mit allen Sektionen
def test_inventory_format_json_full_report() -> None:
    result = runner.invoke(app, ["inventory", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["schema_version"] == "0.0.1"
    assert "os" in data
    assert "cc_suite" in data
    assert "stack" in data
    assert "databases" in data
    assert "apps" in data


# Case 4: --section os filtert auf einzelne Sektion (JSON)
def test_inventory_section_os_only_json() -> None:
    result = runner.invoke(app, ["inventory", "--section", "os", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "os" in data
    # Andere Sektionen sind NICHT im gefilterten Output
    assert "cc_suite" not in data
    assert "stack" not in data
    assert "databases" not in data
    assert "apps" not in data
    # Schema-Header bleibt für Kontext
    assert data["schema_version"] == "0.0.1"


# Case 5: --section cc-suite mit Bindestrich-Choice (Typer-Enum-Mapping)
def test_inventory_section_cc_suite_dash_choice() -> None:
    """Section 'cc-suite' (mit Bindestrich) → Filter auf cc_suite-Subkey."""
    result = runner.invoke(app, ["inventory", "--section", "cc-suite", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "cc_suite" in data
    assert "os" not in data


# Case 6: --section all (Default) gibt alle Sektionen aus
def test_inventory_section_all_includes_everything() -> None:
    result = runner.invoke(app, ["inventory", "--section", "all", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    for key in ("os", "cc_suite", "stack", "databases", "apps"):
        assert key in data


# Case 7: Ungültiges --format raised typer.BadParameter
def test_inventory_invalid_format_raises() -> None:
    result = runner.invoke(app, ["inventory", "--format", "xml"])
    assert result.exit_code != 0


# Case 8: WHITEPAPER-Schema-Match: alle erwarteten Top-Level-Keys + Werte-Typen
def test_inventory_json_matches_whitepaper_schema() -> None:
    """JSON-Output muss WHITEPAPER §JSON-Output-Schema 1:1 matchen."""
    result = runner.invoke(app, ["inventory", "--format", "json"])
    data = json.loads(result.stdout)

    # Top-Level-Keys
    expected_keys = {
        "schema_version", "timestamp", "host",
        "os", "cc_suite", "stack", "databases", "apps",
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

    # apps ist Liste
    assert isinstance(data["apps"], list)


# Case 9: _filter_report mit Section.OS gibt nur OS-Subkey + Header
def test_filter_report_os_only() -> None:
    """Unit-Test der _filter_report-Logik (separat von CLI-Invocation)."""
    report: InventoryReport = {
        "schema_version": "0.0.1",
        "timestamp": "2026-05-08T12:00:00Z",
        "host": "test-box",
        "os": {"id": "ubuntu", "version_id": "24.04",
               "pretty_name": "Ubuntu 24.04 LTS", "kernel": "6.8.0"},
        "cc_suite": {"xed-ccc": "0.2.2", "xed-cca": "0.0.5", "xed-cci": "0.0.1"},
        "stack": {"python3": "3.12.3", "php": None, "node": None},
        "databases": [],
        "apps": [],
    }
    filtered = _filter_report(report, Section.OS)
    assert "os" in filtered
    assert "cc_suite" not in filtered
    assert filtered["schema_version"] == "0.0.1"


# Case 10: _filter_report mit Section.ALL gibt vollständigen Report
def test_filter_report_all_returns_full_report() -> None:
    report: InventoryReport = {
        "schema_version": "0.0.1",
        "timestamp": "2026-05-08T12:00:00Z",
        "host": "test-box",
        "os": {"id": "ubuntu", "version_id": "24.04",
               "pretty_name": "Ubuntu 24.04 LTS", "kernel": "6.8.0"},
        "cc_suite": {"xed-ccc": "0.2.2", "xed-cca": "0.0.5", "xed-cci": "0.0.1"},
        "stack": {"python3": "3.12.3", "php": None, "node": None},
        "databases": [],
        "apps": [],
    }
    filtered = _filter_report(report, Section.ALL)
    assert set(filtered.keys()) == {
        "schema_version", "timestamp", "host",
        "os", "cc_suite", "stack", "databases", "apps",
    }

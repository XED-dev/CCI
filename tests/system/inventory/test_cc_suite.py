"""Tests für cci.system.inventory.cc_suite — pipx-list-JSON-Parsing."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

from cci.system.inventory.cc_suite import collect_cc_suite_info


def _mock_pipx_json(packages: dict[str, str]) -> MagicMock:
    """Helper: baut MagicMock für safe_run-Result mit pipx-list-JSON-Schema."""
    venvs = {
        name: {
            "metadata": {
                "main_package": {
                    "package_version": version,
                },
            },
        }
        for name, version in packages.items()
    }
    return MagicMock(returncode=0, stdout=json.dumps({"venvs": venvs}))


# Case 1: Live-Smoke (pipx existiert auf Workstation; Live-Run)
def test_collect_cc_suite_live_smoke() -> None:
    """Live-Run: pipx list --json wird tatsächlich aufgerufen, alle drei
    Tool-Felder sind Strings (nicht None, nicht KeyError)."""
    info = collect_cc_suite_info()
    assert isinstance(info["xed-ccc"], str)
    assert isinstance(info["xed-cca"], str)
    assert isinstance(info["xed-cci"], str)


# Case 2: Mocked pipx-list mit allen drei Tools installed -> Versionen extrahiert
def test_collect_cc_suite_all_tools_installed() -> None:
    with patch(
        "cci.system.inventory.cc_suite.safe_run",
        return_value=_mock_pipx_json({
            "xed-ccc": "0.2.2",
            "xed-cca": "0.0.5",
            "xed-cci": "0.0.1",
        }),
    ):
        info = collect_cc_suite_info()
    assert info["xed-ccc"] == "0.2.2"
    assert info["xed-cca"] == "0.0.5"
    assert info["xed-cci"] == "0.0.1"


# Case 3: Mocked pipx-list mit fehlendem Tool -> 'unknown'-Fallback
def test_collect_cc_suite_missing_tool_falls_back() -> None:
    """Wenn xed-cci nicht in pipx-Liste, Wert ist 'unknown' statt KeyError."""
    with patch(
        "cci.system.inventory.cc_suite.safe_run",
        return_value=_mock_pipx_json({
            "xed-ccc": "0.2.2",
            # xed-cca + xed-cci fehlen
        }),
    ):
        info = collect_cc_suite_info()
    assert info["xed-ccc"] == "0.2.2"
    assert info["xed-cca"] == "unknown"
    assert info["xed-cci"] == "unknown"


# Case 4: pipx returncode != 0 -> alle Felder 'unknown' (Error-Recovery)
def test_collect_cc_suite_pipx_failure() -> None:
    with patch(
        "cci.system.inventory.cc_suite.safe_run",
        return_value=MagicMock(returncode=1, stdout=""),
    ):
        info = collect_cc_suite_info()
    assert info["xed-ccc"] == "unknown"
    assert info["xed-cca"] == "unknown"
    assert info["xed-cci"] == "unknown"


# Case 5: pipx-Output ist nicht-JSON -> alle Felder 'unknown' (defensive)
def test_collect_cc_suite_invalid_json() -> None:
    with patch(
        "cci.system.inventory.cc_suite.safe_run",
        return_value=MagicMock(returncode=0, stdout="not-json-output"),
    ):
        info = collect_cc_suite_info()
    assert info["xed-ccc"] == "unknown"


# Case 6: pipx nicht installiert (FileNotFoundError) -> alle Felder 'unknown'
def test_collect_cc_suite_pipx_not_installed() -> None:
    with patch(
        "cci.system.inventory.cc_suite.safe_run",
        side_effect=FileNotFoundError("pipx not in PATH"),
    ):
        info = collect_cc_suite_info()
    assert info["xed-ccc"] == "unknown"
    assert info["xed-cca"] == "unknown"
    assert info["xed-cci"] == "unknown"

"""Tests für cci.system.inventory.cc_suite — pipx-list-JSON-Parsing."""

from __future__ import annotations

import json
import subprocess
import sys
from unittest.mock import MagicMock, patch

from cci.system.inventory.cc_suite import (
    _detect_pipx_home,
    collect_cc_suite_info,
)


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


# === v0.0.2 PIPX_HOME-env-Drift-Fix Tests ===


# Case 7: _detect_pipx_home erkennt system-wide pipx (firstboot.sh-Pattern)
def test_detect_pipx_home_system_wide() -> None:
    """sys.executable wie '/opt/pipx/venvs/xed-cci/bin/python3' -> '/opt/pipx'."""
    with patch.object(sys, "executable", "/opt/pipx/venvs/xed-cci/bin/python3"):
        assert _detect_pipx_home() == "/opt/pipx"


# Case 8: _detect_pipx_home erkennt user-default pipx (~/.local/share/pipx)
def test_detect_pipx_home_user_default() -> None:
    """sys.executable wie '/home/u/.local/share/pipx/venvs/.../bin/python3'."""
    with patch.object(
        sys,
        "executable",
        "/home/user/.local/share/pipx/venvs/xed-cci/bin/python3",
    ):
        assert _detect_pipx_home() == "/home/user/.local/share/pipx"


# Case 9: _detect_pipx_home returnt None bei dev-uv-venv (kein 'venvs/'-Segment)
def test_detect_pipx_home_dev_venv_returns_none() -> None:
    """Dev uv-venv-Pfad hat kein 'venvs/'-Segment — Caller nutzt env-default."""
    with patch.object(sys, "executable", "/mnt/data/proj/.venv/bin/python3"):
        assert _detect_pipx_home() is None


# Case 10: collect_cc_suite_info ueberreicht PIPX_HOME-env wenn detected
def test_collect_cc_suite_passes_pipx_home_env() -> None:
    """Wenn _detect_pipx_home Pfad returnt, safe_run-Aufruf bekommt env mit
    PIPX_HOME (Senior-AI039-Fix v0.0.2 2026-05-09)."""
    with patch(
        "cci.system.inventory.cc_suite._detect_pipx_home",
        return_value="/opt/pipx",
    ):
        with patch(
            "cci.system.inventory.cc_suite.safe_run",
            return_value=MagicMock(returncode=0, stdout='{"venvs":{}}'),
        ) as mock_safe_run:
            collect_cc_suite_info()
        call_kwargs = mock_safe_run.call_args.kwargs
        assert "env" in call_kwargs
        assert call_kwargs["env"] is not None
        assert call_kwargs["env"]["PIPX_HOME"] == "/opt/pipx"


# Case 11: collect_cc_suite_info ueberreicht env=None bei Non-pipx-venv
def test_collect_cc_suite_no_env_when_dev_venv() -> None:
    """Wenn _detect_pipx_home None returnt, safe_run-Aufruf hat env=None
    (Parent-Env wird inherited, kein Override)."""
    with patch(
        "cci.system.inventory.cc_suite._detect_pipx_home",
        return_value=None,
    ):
        with patch(
            "cci.system.inventory.cc_suite.safe_run",
            return_value=MagicMock(returncode=0, stdout='{"venvs":{}}'),
        ) as mock_safe_run:
            collect_cc_suite_info()
        call_kwargs = mock_safe_run.call_args.kwargs
        assert call_kwargs.get("env") is None

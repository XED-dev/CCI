"""cc_suite — XED /CC-Suite-Versionen via pipx list --json.

Sammelt installed Versionen von xed-ccc / xed-cca / xed-cci aus pipx
Maschinen-parse-Form (`pipx list --json`). Senior-Pre-Hint H1 (AI039
SS3.2 2026-05-08): JSON-Output > Plain-Text-Regex-Parsing.

Whitelist-Note: `pipx list` ist als Subkommando whitelisted (siehe
safe_run.py). Args nach Subkommando (`--json`) sind frei für Read-Only-
Pattern — keine zusätzliche Whitelist-Erweiterung nötig.

Format-Spec: WHITEPAPER §JSON-Output-Schema §cc_suite-Sektion
(keys mit `-` matchen pipx-Konvention).
"""

from __future__ import annotations

import json
import subprocess
from typing import TypedDict

from cci.system.safe_run import ReadOnlyViolationError, safe_run

# TypedDict mit functional syntax — WHITEPAPER §JSON-Schema nutzt
# `xed-ccc`/`xed-cca`/`xed-cci` als keys mit Bindestrich. Functional
# syntax matcht 1:1 ohne Mapping-Layer in SS5.
CCSuiteInfo = TypedDict(
    "CCSuiteInfo",
    {
        "xed-ccc": str,
        "xed-cca": str,
        "xed-cci": str,
    },
)


_UNKNOWN = "unknown"
_TOOLS = ("xed-ccc", "xed-cca", "xed-cci")


def collect_cc_suite_info() -> CCSuiteInfo:
    """Sammle xed-ccc/xed-cca/xed-cci-Versionen aus `pipx list --json`.

    Bei nicht-installiertem Tool: Wert ist `'unknown'`.
    Bei pipx-Aufruf-Fehler (rc != 0, JSON-Decode-Fail, FileNotFoundError):
    alle drei Felder sind `'unknown'` (defensive).

    Returns:
        CCSuiteInfo mit `xed-ccc`/`xed-cca`/`xed-cci`-Versionen.
    """
    try:
        result = safe_run(["pipx", "list", "--json"], timeout=30.0)
    except (ReadOnlyViolationError, FileNotFoundError, subprocess.TimeoutExpired):
        return _empty_cc_suite_info()

    if result.returncode != 0:
        return _empty_cc_suite_info()

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return _empty_cc_suite_info()

    venvs = data.get("venvs", {})

    def _get_version(pkg_name: str) -> str:
        venv = venvs.get(pkg_name, {})
        meta = venv.get("metadata", {})
        main = meta.get("main_package", {})
        return main.get("package_version", _UNKNOWN)

    return CCSuiteInfo(
        {tool: _get_version(tool) for tool in _TOOLS},  # type: ignore[typeddict-item]
    )


def _empty_cc_suite_info() -> CCSuiteInfo:
    """All-_UNKNOWN-Fallback für pipx-Aufruf-Fehler."""
    return CCSuiteInfo({tool: _UNKNOWN for tool in _TOOLS})  # type: ignore[typeddict-item]

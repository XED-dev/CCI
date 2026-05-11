"""cc_suite — XED /CC-Suite-Versionen via pipx list --json.

Sammelt installed Versionen von xed-ccc / xed-cca / xed-cci aus pipx
Maschinen-parse-Form (`pipx list --json`). Pattern-Anker: JSON-Output
> Plain-Text-Regex-Parsing für Maschinen-stabile Auswertung.

Whitelist-Note: `pipx list` ist als Subkommando whitelisted (siehe
safe_run.py). Args nach Subkommando (`--json`) sind frei für Read-Only-
Pattern — keine zusätzliche Whitelist-Erweiterung nötig.

Format-Spec: WHITEPAPER §JSON-Output-Schema §cc_suite-Sektion
(keys mit `-` matchen pipx-Konvention).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, TypedDict

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


def _detect_pipx_home() -> Optional[str]:
    """Auto-detect PIPX_HOME aus `sys.executable`.

    Wenn cci aus einer pipx-Installation läuft (z.B.
    `/opt/pipx/venvs/xed-cci/bin/python3`), returnt `<PIPX_HOME>`.
    Bei Non-pipx-venvs (dev uv-venv, system Python) returnt `None`
    (Caller nutzt env-default).

    PIPX_HOME-env-Drift-Mitigation: firstboot.sh installiert xed-cci
    system-wide via `PIPX_HOME=/opt/pipx`, aber cci-runtime erbt
    parent-env ohne explizites PIPX_HOME → pipx subprocess sucht in
    user-default `~/.local/share/pipx/` und sieht xed-ccc/xed-cca/xed-cci
    nicht → alle drei Versionen fielen auf `'unknown'`.

    Detection ist robust gegen Symlinks: `sys.executable` ist der
    venv-Python-Pfad UNRESOLVED (PEP 405), Walk via `Path.parents`
    findet `venvs/` ohne Symlink-Follow-Risiko.
    """
    exe = Path(sys.executable)
    for parent in exe.parents:
        if parent.name == "venvs":
            return str(parent.parent)
    return None


def collect_cc_suite_info() -> CCSuiteInfo:
    """Sammle xed-ccc/xed-cca/xed-cci-Versionen aus `pipx list --json`.

    Auto-detect PIPX_HOME: wenn cci aus einer
    pipx-Installation läuft, env-Override an pipx subprocess so dass
    pipx die selbe PIPX_HOME-Sicht hat wie firstboot.sh-install-time.

    Bei nicht-installiertem Tool: Wert ist `'unknown'`.
    Bei pipx-Aufruf-Fehler (rc != 0, JSON-Decode-Fail, FileNotFoundError):
    alle drei Felder sind `'unknown'` (defensive).

    Returns:
        CCSuiteInfo mit `xed-ccc`/`xed-cca`/`xed-cci`-Versionen.
    """
    pipx_home = _detect_pipx_home()
    env: Optional[dict[str, str]] = None
    if pipx_home is not None:
        env = {**os.environ, "PIPX_HOME": pipx_home}

    try:
        result = safe_run(["pipx", "list", "--json"], timeout=30.0, env=env)
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

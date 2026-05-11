"""stack — Programmier-Stack-Versionen (python3 + php + node).

Pattern-Anker:
- python3 ist DER LAUFENDE INTERPRETER. `sys.version_info` ist
  authoritativ + Stdlib-only — KEIN subprocess für python3-Version.
- php/node sind external — `shutil.which()` Detection-only-wenn-installiert,
  dann `safe_run` mit Whitelist-validated `--version`.

Detection-Pattern: wenn Tool nicht im PATH (`shutil.which()` returnt None),
ist Wert `None` (= „not installed"). Pattern matcht WHITEPAPER §JSON-
Schema-Spec wo `node: null` möglich ist.

Whitelist-Update für php/node (commit zusammen mit dieser Datei in SS3.3):
`safe_run.py` COMMAND_WHITELIST hat jetzt:
  "php": frozenset({"--version", "-v"})
  "node": frozenset({"--version", "-v"})
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from typing import Optional, TypedDict

from cci.system.safe_run import ReadOnlyViolationError, safe_run


class StackInfo(TypedDict):
    """Programmier-Stack-Versionen matching WHITEPAPER §JSON-Schema."""

    python3: str
    php: Optional[str]
    node: Optional[str]


def _python3_version() -> str:
    """Python3-Version aus laufendem Interpreter via Stdlib (sys.version_info).

    Authoritativ: kein subprocess nötig, weil cci selbst in Python läuft
    und sys.version_info immer den laufenden Interpreter beschreibt.
    """
    v = sys.version_info
    return f"{v.major}.{v.minor}.{v.micro}"


def _external_tool_version(tool: str) -> Optional[str]:
    """External-Tool-Version via `<tool> --version`.

    Detection-only-wenn-installiert: `shutil.which()` prüft PATH.
    Wenn nicht im PATH, Return None (= „not installed").

    Wenn im PATH: `safe_run([tool, '--version'])` und Versions-String
    aus stdout extrahieren. Bei Fehler oder Parse-Fail: None.
    """
    if shutil.which(tool) is None:
        return None

    try:
        result = safe_run([tool, "--version"], timeout=10.0)
    except (ReadOnlyViolationError, FileNotFoundError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    # Output-Parse: erste X.Y.Z-Sequenz aus stdout (oder stderr für ältere Tools).
    # Beispiele:
    #   "PHP 8.2.18 (cli) (built: ...)"           -> 8.2.18
    #   "v22.18.0"                                  -> 22.18.0
    #   "Node.js v20.10.0"                          -> 20.10.0
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    match = re.search(r"(\d+\.\d+\.\d+)", output)
    return match.group(1) if match else None


def collect_stack_info() -> StackInfo:
    """Sammle Programmier-Stack-Versionen.

    Returns:
        StackInfo mit python3 (immer Wert) + php/node (Optional[str]).
    """
    return StackInfo(
        python3=_python3_version(),
        php=_external_tool_version("php"),
        node=_external_tool_version("node"),
    )

"""box_class — Box-Klassen-Verifikation Pre-Step für cci typo3 (v0.0.10).

Hard-Checks vor jeder Box-Klassen-Inventur. Wenn die Box keine
WordOps-LEMP-Ubuntu-LTS-Box ist (Box-Klassen-Mismatch), wird die
Inventur-Logik nicht ausgeführt — Caller (z.B. `inventory_command`)
soll `verify_typo3_box_class()` vor `collect_sites_info()` aufrufen
und bei `ok=False` mit Exit 2 + klare Fehlermeldung abbrechen.

Architektur-Anker (DevOps-Direktive 2026-05-13):
cci adressiert eingegrenzte Box-Klassen, NICHT generische Linux-
Inventur. Pre-Step ist das strukturelle Hard-Gate gegen unsicheres
Verhalten auf Box-Mismatch-Boxen.

Drei Hard-Checks (alle müssen passen):
  1. /etc/os-release: ID=ubuntu + VERSION_ID in {22.04, 24.04}
  2. `wo` (WordOps-CLI) im PATH (shutil.which)
  3. nginx-wo-Paket installiert (dpkg-query -W nginx-wo)

Stack-Komponenten (Multi-PHP, MariaDB, Solr, Composer) bleiben bewusst
in der Stack-Inventur (v0.0.12) — saubere Schicht-Trennung zwischen
Box-Klasse-Identifikation und Stack-Inventur.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import NamedTuple

from cci.system.safe_run import ReadOnlyViolationError, safe_run

_OS_RELEASE_PATH = Path("/etc/os-release")
_SUPPORTED_UBUNTU_VERSIONS = frozenset({"22.04", "24.04"})


class BoxClassCheckResult(NamedTuple):
    """Ergebnis von verify_typo3_box_class().

    `ok=True`: alle Hard-Checks passed.
    `ok=False`: ein oder mehrere Mismatches; `errors` enthält klare
    Fehlermeldungen für SysOps (1 Zeile pro Mismatch).
    `diagnostics` enthält pro Check den Live-Wert (für Output-Anzeige
    bei Mismatch — z.B. "Distro 'debian 12', Version 'bookworm'").
    """

    ok: bool
    errors: list[str]
    diagnostics: dict[str, str]


def _parse_os_release(content: str) -> dict[str, str]:
    """Pure-Parse: /etc/os-release-Inhalt → flat dict.

    Format: KEY=value oder KEY="value with spaces". Defensive: invalid
    Lines werden ignoriert (kein Crash bei unerwartetem Format).
    """
    fields: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        # Quotes entfernen (sowohl " als auch ')
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
            val = val[1:-1]
        fields[key.strip()] = val
    return fields


def _check_ubuntu_lts() -> tuple[bool, str, str]:
    """Prüft /etc/os-release auf Ubuntu LTS 22.04 oder 24.04.

    Returns:
        (ok, diagnostic_value, error_message). Bei ok=True ist
        error_message leer; diagnostic_value ist immer informativ.
    """
    try:
        content = _OS_RELEASE_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return (False, "unreadable", "/etc/os-release nicht lesbar")

    fields = _parse_os_release(content)
    distro_id = fields.get("ID", "unknown")
    version_id = fields.get("VERSION_ID", "unknown")
    diag = f"{distro_id} {version_id}"

    if distro_id != "ubuntu":
        return (
            False,
            diag,
            f"Box ist {distro_id!r} (erwartet: Ubuntu LTS 22.04 oder 24.04)",
        )

    if version_id not in _SUPPORTED_UBUNTU_VERSIONS:
        return (
            False,
            diag,
            f"Ubuntu-Version {version_id!r} (erwartet: 22.04 oder 24.04 LTS)",
        )

    return (True, diag, "")


def _check_wo_binary() -> tuple[bool, str, str]:
    """Prüft ob `wo` (WordOps-CLI) im PATH ist."""
    wo_path = shutil.which("wo")
    if wo_path is None:
        return (False, "missing", "WordOps-CLI `wo` nicht im PATH")
    return (True, wo_path, "")


def _check_nginx_wo_installed() -> tuple[bool, str, str]:
    """Prüft ob nginx-wo-Paket via dpkg-query installiert ist.

    `dpkg-query -W -f='${Status}' nginx-wo` returns:
      - exit 0 + "install ok installed" wenn installed
      - exit 0 + "deinstall ok config-files" wenn purgable-Rest
      - exit 1 wenn package unbekannt

    Wir akzeptieren nur „installed" als Match.
    """
    try:
        result = safe_run(
            ["dpkg-query", "-W", "-f=${Status}\n", "nginx-wo"],
            timeout=5.0,
        )
    except (FileNotFoundError, ReadOnlyViolationError) as exc:
        return (False, "dpkg-query unavailable", f"dpkg-query-Aufruf gescheitert: {exc}")

    if result.returncode != 0:
        return (
            False,
            "not-installed",
            "nginx-wo-Paket nicht installiert (dpkg-query: unbekannt)",
        )

    status_line = result.stdout.strip()
    if "installed" not in status_line.lower():
        return (
            False,
            status_line,
            f"nginx-wo-Paket-Status: {status_line!r} (erwartet: 'install ok installed')",
        )

    return (True, status_line, "")


def verify_typo3_box_class() -> BoxClassCheckResult:
    """Verifiziere TYPO3-Box-Klasse (WordOps-LEMP-Ubuntu-LTS).

    Führt alle drei Hard-Checks aus (ohne early-exit, damit SysOps
    bei Mismatch alle Probleme auf einmal sieht statt iteratives
    Re-Run).

    Returns:
        BoxClassCheckResult mit ok=True wenn alle Checks passen,
        sonst ok=False mit errors-Liste (1 Zeile pro Mismatch) +
        diagnostics-Dict (Live-Werte pro Check).
    """
    errors: list[str] = []
    diagnostics: dict[str, str] = {}

    ubuntu_ok, ubuntu_diag, ubuntu_err = _check_ubuntu_lts()
    diagnostics["os"] = ubuntu_diag
    if not ubuntu_ok:
        errors.append(ubuntu_err)

    wo_ok, wo_diag, wo_err = _check_wo_binary()
    diagnostics["wo_binary"] = wo_diag
    if not wo_ok:
        errors.append(wo_err)

    nginx_ok, nginx_diag, nginx_err = _check_nginx_wo_installed()
    diagnostics["nginx_wo"] = nginx_diag
    if not nginx_ok:
        errors.append(nginx_err)

    return BoxClassCheckResult(
        ok=(not errors),
        errors=errors,
        diagnostics=diagnostics,
    )


__all__ = [
    "BoxClassCheckResult",
    "verify_typo3_box_class",
]

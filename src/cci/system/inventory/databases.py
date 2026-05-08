"""databases — Datenbank-Engines via dpkg-query + systemctl is-active.

Pattern fortgesetzt aus SS3.3 (Stdlib-Idiomatik bevorzugt, safe_run
mit konkreter Whitelist sonst):
- `dpkg-query -W -f` für purpose-built Read-Only-Paket-Query (nicht
  general-purpose `dpkg`)
- `systemctl is-active <service>` für Service-Status

Bekannte Engines (Phase 1 v0.0.1):
- mysql-server  (engine: 'mysql',      service: 'mysql')
- mariadb-server (engine: 'mariadb',   service: 'mariadb')
- postgresql    (engine: 'postgresql', service: 'postgresql')

Weitere Engines (redis, mongodb, sqlite-cli, ...) als Backlog für v0.x.

Format-Spec: WHITEPAPER §JSON-Output-Schema §databases ist Liste von
{engine, version, service_active}-Records.
"""

from __future__ import annotations

import subprocess
from typing import Optional, TypedDict

from cci.system.safe_run import ReadOnlyViolationError, safe_run


class DatabaseInfo(TypedDict):
    engine: str
    version: str
    service_active: bool


# (dpkg-Package, engine-Name, systemctl-Service-Name)
_DB_PACKAGES: tuple[tuple[str, str, str], ...] = (
    ("mysql-server", "mysql", "mysql"),
    ("mariadb-server", "mariadb", "mariadb"),
    ("postgresql", "postgresql", "postgresql"),
)

_INSTALLED_STATUS_PREFIX = "install ok installed"


def _dpkg_status(pkg: str) -> Optional[tuple[str, str]]:
    """Returnt (version, dpkg-status) wenn pkg in dpkg-DB, sonst None.

    dpkg-Status ist z.B. 'install ok installed' oder 'deinstall ok
    config-files'. Caller filtert auf 'install ok installed'.
    """
    try:
        result = safe_run(
            ["dpkg-query", "-W", "-f", "${Version}|${Status}", pkg],
            timeout=10.0,
        )
    except (
        ReadOnlyViolationError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        return None

    if result.returncode != 0:
        return None

    parts = result.stdout.strip().split("|", 1)
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


def _service_active(service: str) -> bool:
    """systemctl is-active -> True wenn rc=0 und stdout.strip() == 'active'.

    Defensive: bei Whitelist-Verstoß / FileNotFoundError / Timeout -> False
    (Service-Status nicht determinierbar = sicher als inaktiv behandeln).
    """
    try:
        result = safe_run(["systemctl", "is-active", service], timeout=5.0)
    except (
        ReadOnlyViolationError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        return False
    return result.returncode == 0 and result.stdout.strip() == "active"


def collect_databases_info() -> list[DatabaseInfo]:
    """Sammle installed Datenbank-Engines + Versionen + Service-Status.

    Iteriert _DB_PACKAGES, filtert auf 'install ok installed', sammelt
    Service-Status via systemctl is-active.

    Returns:
        Liste von DatabaseInfo-Records (leer wenn keine Engine installed).
    """
    databases: list[DatabaseInfo] = []
    for pkg, engine, service in _DB_PACKAGES:
        status = _dpkg_status(pkg)
        if status is None:
            continue
        version, dpkg_status = status
        if not dpkg_status.startswith(_INSTALLED_STATUS_PREFIX):
            continue
        databases.append(
            DatabaseInfo(
                engine=engine,
                version=version,
                service_active=_service_active(service),
            )
        )
    return databases

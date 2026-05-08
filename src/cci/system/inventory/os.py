"""os — OS-Inventur-Sektion (Stdlib-only, ohne safe_run).

Strukturell read-only via Stdlib (`platform.freedesktop_os_release` +
`os.uname`). Kein subprocess nötig — strukturell noch sicherer als
Whitelist-validated subprocess.

Senior-Pattern-Anker (AI039 SS3.1 2026-05-08):
„Stdlib-Idiomatik als ersten Check" — bevor `safe_run`-subprocess
gewählt wird, prüfen ob Python-Stdlib bereits eine purpose-built
Funktion hat. Hier:

- `platform.freedesktop_os_release()` (Python 3.10+ stdlib) für
  /etc/os-release-Parsing — KEIN manuelles KEY=VALUE-Parsing
- `os.uname().release` für Kernel-Version — KEIN subprocess `uname -r`

Format-Spec: WHITEPAPER §JSON-Output-Schema §`os`-Sektion.
"""

from __future__ import annotations

import os
import platform
from typing import TypedDict


class OSInfo(TypedDict):
    """OS-Inventur-Daten matching WHITEPAPER §JSON-Schema."""

    id: str
    version_id: str
    pretty_name: str
    kernel: str


_UNKNOWN = "unknown"


def collect_os_info() -> OSInfo:
    """Sammle OS-Identität + Kernel-Version via Stdlib.

    Quellen:
    - `/etc/os-release` via `platform.freedesktop_os_release()`
    - Kernel-Version via `os.uname().release`

    Bei fehlenden `/etc/os-release`-Feldern: `'unknown'` als Fallback
    (statt KeyError/Crash). Operator sieht klar dass Feld nicht
    verfügbar ist.

    Bei nicht-lesbarem `/etc/os-release` (OSError, sehr selten):
    alle drei OS-Felder fallen auf `'unknown'`, Kernel kommt weiterhin
    via `os.uname()`.

    Returns:
        OSInfo mit id, version_id, pretty_name, kernel.
    """
    try:
        os_release = platform.freedesktop_os_release()
    except OSError:
        os_release = {}

    return OSInfo(
        id=os_release.get("ID", _UNKNOWN),
        version_id=os_release.get("VERSION_ID", _UNKNOWN),
        pretty_name=os_release.get("PRETTY_NAME", _UNKNOWN),
        kernel=os.uname().release,
    )

"""Tests für cci.system.inventory.os — OS-Inventur-Sektion."""

from __future__ import annotations

import re
from unittest.mock import patch

from cci.system.inventory.os import collect_os_info


# Case 1: Echter Run auf Linux (Workstation hat /etc/os-release + Kernel)
def test_collect_os_info_real_run() -> None:
    """Live-Run liefert alle vier Felder als nicht-leere Strings."""
    info = collect_os_info()
    # OSInfo TypedDict-Keys vorhanden + nicht-None
    assert isinstance(info["id"], str)
    assert isinstance(info["version_id"], str)
    assert isinstance(info["pretty_name"], str)
    assert isinstance(info["kernel"], str)
    # Kernel ist auf jedem Linux verfügbar
    assert info["kernel"]


# Case 2: Fehlende Felder im os-release -> 'unknown' Fallback statt KeyError
def test_collect_os_info_missing_fields_fallback() -> None:
    """Wenn /etc/os-release nur ID + VERSION_ID hat (PRETTY_NAME fehlt),
    fällt pretty_name auf 'unknown' zurück."""
    with patch(
        "cci.system.inventory.os.platform.freedesktop_os_release",
        return_value={"ID": "ubuntu", "VERSION_ID": "24.04"},
    ):
        info = collect_os_info()
    assert info["id"] == "ubuntu"
    assert info["version_id"] == "24.04"
    assert info["pretty_name"] == "unknown"


# Case 3: /etc/os-release nicht lesbar (OSError) -> alle OS-Felder 'unknown'
def test_collect_os_info_no_os_release_file() -> None:
    """Wenn platform.freedesktop_os_release OSError wirft, fallen
    id/version_id/pretty_name auf 'unknown' zurück. Kernel bleibt
    via os.uname() verfügbar."""
    with patch(
        "cci.system.inventory.os.platform.freedesktop_os_release",
        side_effect=OSError("No /etc/os-release"),
    ):
        info = collect_os_info()
    assert info["id"] == "unknown"
    assert info["version_id"] == "unknown"
    assert info["pretty_name"] == "unknown"
    # Kernel kommt von os.uname() und ist auf Linux immer verfügbar
    assert info["kernel"]


# Case 4: Kernel-String matcht typisches Linux-Kernel-Pattern (X.Y.Z-...)
def test_kernel_string_format() -> None:
    """Linux-Kernel-Versionen folgen Major.Minor.Patch[-suffix]-Pattern.

    Beispiele: '6.8.0-78-generic', '5.15.0-105-generic', '6.5.0-1027-azure'.
    """
    info = collect_os_info()
    assert re.match(r"^\d+\.\d+\.\d+", info["kernel"]), (
        f"Kernel-String entspricht nicht erwartetem Pattern: "
        f"{info['kernel']!r}"
    )

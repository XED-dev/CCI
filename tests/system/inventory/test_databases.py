"""Tests für cci.system.inventory.databases."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cci.system.inventory.databases import (
    _dpkg_status,
    _service_active,
    collect_databases_info,
)


# Case 1: dpkg-query mit installed pkg -> (version, status)-Tuple
def test_dpkg_status_installed() -> None:
    with patch(
        "cci.system.inventory.databases.safe_run",
        return_value=MagicMock(returncode=0, stdout="8.0.39|install ok installed"),
    ):
        result = _dpkg_status("mysql-server")
    assert result == ("8.0.39", "install ok installed")


# Case 2: dpkg-query mit nicht-installed pkg (rc != 0) -> None
def test_dpkg_status_not_installed() -> None:
    with patch(
        "cci.system.inventory.databases.safe_run",
        return_value=MagicMock(returncode=1, stdout=""),
    ):
        result = _dpkg_status("mysql-server")
    assert result is None


# Case 3: systemctl is-active 'active' -> True
def test_service_active_true() -> None:
    with patch(
        "cci.system.inventory.databases.safe_run",
        return_value=MagicMock(returncode=0, stdout="active\n"),
    ):
        assert _service_active("mysql") is True


# Case 4: systemctl is-active 'inactive' (rc != 0) -> False
def test_service_active_false() -> None:
    with patch(
        "cci.system.inventory.databases.safe_run",
        return_value=MagicMock(returncode=3, stdout="inactive\n"),
    ):
        assert _service_active("mysql") is False


# Case 5: collect_databases_info — keine DB installed -> leere Liste
def test_collect_databases_none_installed() -> None:
    with patch(
        "cci.system.inventory.databases.safe_run",
        return_value=MagicMock(returncode=1, stdout=""),
    ):
        result = collect_databases_info()
    assert result == []


# Case 6: collect_databases_info — mysql installed + active
def test_collect_databases_mysql_only() -> None:
    """Mysql installed + active, mariadb/postgres nicht installed."""

    def _safe_run_dispatch(cmd, **kwargs):
        if cmd[0] == "dpkg-query" and "mysql-server" in cmd:
            return MagicMock(returncode=0, stdout="8.0.39|install ok installed")
        if cmd[0] == "dpkg-query":
            return MagicMock(returncode=1, stdout="")
        if cmd[0] == "systemctl" and cmd[2] == "mysql":
            return MagicMock(returncode=0, stdout="active\n")
        return MagicMock(returncode=3, stdout="inactive\n")

    with patch(
        "cci.system.inventory.databases.safe_run",
        side_effect=_safe_run_dispatch,
    ):
        result = collect_databases_info()
    assert len(result) == 1
    assert result[0]["engine"] == "mysql"
    assert result[0]["version"] == "8.0.39"
    assert result[0]["service_active"] is True


# Case 7: dpkg-query mit deinstall-status (config-files) -> nicht in Liste
def test_collect_databases_skips_deinstalled() -> None:
    """Pakete mit 'deinstall ok config-files' werden ignoriert (nicht
    aktiv installed, nur Konfig-Reste)."""

    def _safe_run_dispatch(cmd, **kwargs):
        if cmd[0] == "dpkg-query" and "mysql-server" in cmd:
            return MagicMock(returncode=0, stdout="8.0.39|deinstall ok config-files")
        if cmd[0] == "dpkg-query":
            return MagicMock(returncode=1, stdout="")
        return MagicMock(returncode=3, stdout="")

    with patch(
        "cci.system.inventory.databases.safe_run",
        side_effect=_safe_run_dispatch,
    ):
        result = collect_databases_info()
    assert result == []


# Case 8: Live-Smoke (echter Workstation-State)
def test_collect_databases_live_smoke() -> None:
    """Live-Run gibt Liste zurück (kann leer sein)."""
    result = collect_databases_info()
    assert isinstance(result, list)
    for db in result:
        assert isinstance(db["engine"], str)
        assert isinstance(db["version"], str)
        assert isinstance(db["service_active"], bool)

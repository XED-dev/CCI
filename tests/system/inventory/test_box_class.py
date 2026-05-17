"""Tests für cci.system.inventory.box_class — TYPO3-Box-Klassen-Verifikation (v0.0.10)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from cci.system.inventory.box_class import (
    BoxClassCheckResult,
    _check_nginx_wo_installed,
    _check_ubuntu_lts,
    _check_wo_binary,
    _parse_os_release,
    verify_typo3_box_class,
)


# ---------------------------------------------------------------------------
# _parse_os_release (Pure-Parse)
# ---------------------------------------------------------------------------


def test_parse_os_release_extracts_quoted_and_unquoted() -> None:
    """Standard-os-release-Format mit Quotes + Unquoted-Werten."""
    content = (
        'NAME="Ubuntu"\n'
        'VERSION_ID="22.04"\n'
        'ID=ubuntu\n'
        'PRETTY_NAME="Ubuntu 22.04.5 LTS"\n'
    )
    fields = _parse_os_release(content)
    assert fields["NAME"] == "Ubuntu"
    assert fields["VERSION_ID"] == "22.04"
    assert fields["ID"] == "ubuntu"
    assert fields["PRETTY_NAME"] == "Ubuntu 22.04.5 LTS"


def test_parse_os_release_ignores_comment_and_empty_lines() -> None:
    """Comment-Lines (^#) und leere Lines werden ignoriert."""
    content = (
        '# This is a comment\n'
        '\n'
        'ID=ubuntu\n'
        '   \n'
        'VERSION_ID="24.04"\n'
    )
    fields = _parse_os_release(content)
    assert fields == {"ID": "ubuntu", "VERSION_ID": "24.04"}


def test_parse_os_release_defensive_invalid_lines() -> None:
    """Lines ohne '=' werden ignoriert (defensive)."""
    content = (
        'ID=ubuntu\n'
        'NOT_A_KEY_VALUE_PAIR\n'
        'VERSION_ID="22.04"\n'
    )
    fields = _parse_os_release(content)
    assert fields == {"ID": "ubuntu", "VERSION_ID": "22.04"}


# ---------------------------------------------------------------------------
# _check_ubuntu_lts (mit mocked _OS_RELEASE_PATH)
# ---------------------------------------------------------------------------


def test_check_ubuntu_lts_match_22_04(tmp_path: Path) -> None:
    """Ubuntu 22.04 → ok=True."""
    os_release = tmp_path / "os-release"
    os_release.write_text(
        'ID=ubuntu\nVERSION_ID="22.04"\nPRETTY_NAME="Ubuntu 22.04.5 LTS"\n',
        encoding="utf-8",
    )
    with patch("cci.system.inventory.box_class._OS_RELEASE_PATH", os_release):
        ok, diag, err = _check_ubuntu_lts()
    assert ok is True
    assert "ubuntu" in diag
    assert "22.04" in diag
    assert err == ""


def test_check_ubuntu_lts_match_24_04(tmp_path: Path) -> None:
    """Ubuntu 24.04 → ok=True."""
    os_release = tmp_path / "os-release"
    os_release.write_text(
        'ID=ubuntu\nVERSION_ID="24.04"\n', encoding="utf-8"
    )
    with patch("cci.system.inventory.box_class._OS_RELEASE_PATH", os_release):
        ok, _, err = _check_ubuntu_lts()
    assert ok is True
    assert err == ""


def test_check_ubuntu_lts_mismatch_debian(tmp_path: Path) -> None:
    """Debian → ok=False mit Fehlermeldung."""
    os_release = tmp_path / "os-release"
    os_release.write_text(
        'ID=debian\nVERSION_ID="12"\n', encoding="utf-8"
    )
    with patch("cci.system.inventory.box_class._OS_RELEASE_PATH", os_release):
        ok, diag, err = _check_ubuntu_lts()
    assert ok is False
    assert "debian" in diag
    assert "debian" in err
    assert "Ubuntu" in err


def test_check_ubuntu_lts_mismatch_old_ubuntu(tmp_path: Path) -> None:
    """Ubuntu 20.04 (out of LTS-Support-Range) → ok=False."""
    os_release = tmp_path / "os-release"
    os_release.write_text(
        'ID=ubuntu\nVERSION_ID="20.04"\n', encoding="utf-8"
    )
    with patch("cci.system.inventory.box_class._OS_RELEASE_PATH", os_release):
        ok, _, err = _check_ubuntu_lts()
    assert ok is False
    assert "20.04" in err
    assert "22.04" in err or "24.04" in err


def test_check_ubuntu_lts_missing_os_release_file(tmp_path: Path) -> None:
    """Fehlende /etc/os-release → ok=False mit klarer Meldung."""
    missing = tmp_path / "missing-os-release"
    with patch("cci.system.inventory.box_class._OS_RELEASE_PATH", missing):
        ok, _, err = _check_ubuntu_lts()
    assert ok is False
    assert "nicht lesbar" in err


# ---------------------------------------------------------------------------
# _check_wo_binary (mit mocked shutil.which)
# ---------------------------------------------------------------------------


def test_check_wo_binary_available() -> None:
    """`wo` im PATH → ok=True mit Pfad als Diagnostic."""
    with patch(
        "cci.system.inventory.box_class.shutil.which", return_value="/usr/local/bin/wo"
    ):
        ok, diag, err = _check_wo_binary()
    assert ok is True
    assert diag == "/usr/local/bin/wo"
    assert err == ""


def test_check_wo_binary_missing() -> None:
    """`wo` nicht im PATH → ok=False."""
    with patch(
        "cci.system.inventory.box_class.shutil.which", return_value=None
    ):
        ok, diag, err = _check_wo_binary()
    assert ok is False
    assert diag == "missing"
    assert "wo" in err
    assert "PATH" in err


# ---------------------------------------------------------------------------
# _check_nginx_wo_installed (mocked safe_run)
# ---------------------------------------------------------------------------


def test_check_nginx_wo_installed_ok() -> None:
    """dpkg-query: 'install ok installed' → ok=True."""
    mock_result = MagicMock(returncode=0, stdout="install ok installed\n")
    with patch(
        "cci.system.inventory.box_class.safe_run", return_value=mock_result
    ):
        ok, diag, err = _check_nginx_wo_installed()
    assert ok is True
    assert "installed" in diag
    assert err == ""


def test_check_nginx_wo_not_installed() -> None:
    """dpkg-query exit 1 (package unbekannt) → ok=False."""
    mock_result = MagicMock(returncode=1, stdout="")
    with patch(
        "cci.system.inventory.box_class.safe_run", return_value=mock_result
    ):
        ok, _, err = _check_nginx_wo_installed()
    assert ok is False
    assert "nginx-wo" in err


def test_check_nginx_wo_purged() -> None:
    """dpkg-query: 'deinstall ok config-files' (purgable rest) → ok=False."""
    mock_result = MagicMock(returncode=0, stdout="deinstall ok config-files\n")
    with patch(
        "cci.system.inventory.box_class.safe_run", return_value=mock_result
    ):
        ok, diag, err = _check_nginx_wo_installed()
    assert ok is False
    assert "deinstall" in diag
    assert "nginx-wo" in err


def test_check_nginx_wo_subprocess_error() -> None:
    """Bei FileNotFoundError (dpkg-query nicht da) → ok=False."""
    with patch(
        "cci.system.inventory.box_class.safe_run",
        side_effect=FileNotFoundError,
    ):
        ok, _, err = _check_nginx_wo_installed()
    assert ok is False
    assert "dpkg-query" in err


# ---------------------------------------------------------------------------
# verify_typo3_box_class (Integration)
# ---------------------------------------------------------------------------


def test_verify_typo3_box_class_all_match(tmp_path: Path) -> None:
    """Alle drei Checks passen → ok=True, errors leer."""
    os_release = tmp_path / "os-release"
    os_release.write_text(
        'ID=ubuntu\nVERSION_ID="22.04"\n', encoding="utf-8"
    )
    mock_dpkg = MagicMock(returncode=0, stdout="install ok installed\n")

    with patch(
        "cci.system.inventory.box_class._OS_RELEASE_PATH", os_release
    ), patch(
        "cci.system.inventory.box_class.shutil.which", return_value="/usr/local/bin/wo"
    ), patch(
        "cci.system.inventory.box_class.safe_run", return_value=mock_dpkg
    ):
        result = verify_typo3_box_class()

    assert isinstance(result, BoxClassCheckResult)
    assert result.ok is True
    assert result.errors == []
    assert "ubuntu" in result.diagnostics["os"]
    assert result.diagnostics["wo_binary"] == "/usr/local/bin/wo"
    assert "installed" in result.diagnostics["nginx_wo"]


def test_verify_typo3_box_class_all_mismatch(tmp_path: Path) -> None:
    """Alle drei Checks fail → ok=False, errors hat 3 Einträge."""
    os_release = tmp_path / "os-release"
    os_release.write_text(
        'ID=debian\nVERSION_ID="12"\n', encoding="utf-8"
    )
    mock_dpkg = MagicMock(returncode=1, stdout="")

    with patch(
        "cci.system.inventory.box_class._OS_RELEASE_PATH", os_release
    ), patch(
        "cci.system.inventory.box_class.shutil.which", return_value=None
    ), patch(
        "cci.system.inventory.box_class.safe_run", return_value=mock_dpkg
    ):
        result = verify_typo3_box_class()

    assert result.ok is False
    assert len(result.errors) == 3
    # Errors enthalten Distro-Mismatch + wo-fehlt + nginx-wo-fehlt
    error_text = " ".join(result.errors)
    assert "debian" in error_text
    assert "wo" in error_text
    assert "nginx-wo" in error_text


def test_verify_typo3_box_class_partial_mismatch_ubuntu_ok_wo_missing(
    tmp_path: Path,
) -> None:
    """Ubuntu OK, wo OK, nginx-wo missing → ok=False mit 1 error."""
    os_release = tmp_path / "os-release"
    os_release.write_text(
        'ID=ubuntu\nVERSION_ID="24.04"\n', encoding="utf-8"
    )
    mock_dpkg = MagicMock(returncode=1, stdout="")

    with patch(
        "cci.system.inventory.box_class._OS_RELEASE_PATH", os_release
    ), patch(
        "cci.system.inventory.box_class.shutil.which",
        return_value="/usr/local/bin/wo",
    ), patch(
        "cci.system.inventory.box_class.safe_run", return_value=mock_dpkg
    ):
        result = verify_typo3_box_class()

    assert result.ok is False
    assert len(result.errors) == 1
    assert "nginx-wo" in result.errors[0]
    # diagnostics zeigen Live-Werte für alle drei Checks
    assert "ubuntu" in result.diagnostics["os"]
    assert result.diagnostics["wo_binary"] == "/usr/local/bin/wo"

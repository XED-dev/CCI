"""Tests für cci.system.inventory.stack — python3 + php + node."""

from __future__ import annotations

import re
import sys
from unittest.mock import MagicMock, patch

from cci.system.inventory.stack import (
    _external_tool_version,
    _python3_version,
    collect_stack_info,
)


# Case 1: python3-Version aus sys.version_info matcht laufenden Interpreter
def test_python3_version_matches_sys_version() -> None:
    """sys.version_info ist authoritativ — Live-Run liefert X.Y.Z des
    laufenden Python."""
    version = _python3_version()
    expected = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    assert version == expected
    assert re.match(r"^\d+\.\d+\.\d+$", version)


# Case 2: external-tool nicht im PATH -> None (Detection-only-wenn-installiert)
def test_external_tool_not_installed() -> None:
    with patch("cci.system.inventory.stack.shutil.which", return_value=None):
        result = _external_tool_version("php")
    assert result is None


# Case 3: external-tool im PATH + Version-Parse erfolgreich
def test_external_tool_version_parsed() -> None:
    """Mocked PHP --version Output -> Version extrahiert."""
    with patch("cci.system.inventory.stack.shutil.which", return_value="/usr/bin/php"):
        with patch(
            "cci.system.inventory.stack.safe_run",
            return_value=MagicMock(
                returncode=0,
                stdout="PHP 8.2.18 (cli) (built: Jan 16 2024)\n",
                stderr="",
            ),
        ):
            result = _external_tool_version("php")
    assert result == "8.2.18"


# Case 4: external-tool im PATH + Output in stderr (ältere node-Versionen)
def test_external_tool_version_from_stderr() -> None:
    """Manche Tools schreiben Version auf stderr — _external_tool_version
    sucht beide Streams ab."""
    with patch("cci.system.inventory.stack.shutil.which", return_value="/usr/bin/node"):
        with patch(
            "cci.system.inventory.stack.safe_run",
            return_value=MagicMock(
                returncode=0,
                stdout="",
                stderr="v22.18.0\n",
            ),
        ):
            result = _external_tool_version("node")
    assert result == "22.18.0"


# Case 5: external-tool im PATH aber rc != 0 -> None (Recovery)
def test_external_tool_runtime_error() -> None:
    with patch("cci.system.inventory.stack.shutil.which", return_value="/usr/bin/php"):
        with patch(
            "cci.system.inventory.stack.safe_run",
            return_value=MagicMock(returncode=1, stdout="", stderr=""),
        ):
            result = _external_tool_version("php")
    assert result is None


# Case 6: collect_stack_info Live-Smoke (echter Workstation-State)
def test_collect_stack_live_smoke() -> None:
    """Live-Run: python3 ist immer da (cci läuft selbst in Python),
    php/node sind Optional je nach Workstation."""
    info = collect_stack_info()
    assert isinstance(info["python3"], str)
    assert re.match(r"^\d+\.\d+\.\d+$", info["python3"])
    assert info["php"] is None or isinstance(info["php"], str)
    assert info["node"] is None or isinstance(info["node"], str)

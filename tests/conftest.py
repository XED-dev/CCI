"""Pytest-Konfiguration für xed-cci Tests.

Autouse-Fixtures für CLI-Invocation-Tests die Box-Klassen-Pre-Step mocken
müssen (v0.0.10): Workstation hat keinen WordOps-Stack, production-Code
würde Exit 2 auf jedem `cci typo3`-Aufruf werfen. Mock returnt ok=True
für alle Test-Module außer:
- `test_box_class.py` (testet den Check direkt, kein Mock)
- Tests mit `exits_on_box_mismatch` im Namen (override Mock per
  explizitem `patch(..., return_value=ok=False)`)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cci.system.inventory.box_class import BoxClassCheckResult


@pytest.fixture(autouse=True)
def _mock_box_class_check_ok(request):
    """Auto-Mock verify_typo3_box_class für CLI-Invocation-Tests."""
    # test_box_class.py testet den Check direkt — kein Mock
    if "test_box_class" in request.node.module.__name__:
        yield
        return

    # Tests die Box-Class-Mismatch explizit prüfen — kein Auto-Mock,
    # sie setzen eigenen Mock mit ok=False
    if "exits_on_box_mismatch" in request.node.name:
        yield
        return

    with patch(
        "cci.commands.inventory.verify_typo3_box_class",
        return_value=BoxClassCheckResult(
            ok=True,
            errors=[],
            diagnostics={
                "os": "test-mock-ubuntu 22.04",
                "wo_binary": "test-mock-/usr/local/bin/wo",
                "nginx_wo": "test-mock-installed",
            },
        ),
    ):
        yield

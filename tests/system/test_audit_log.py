"""Tests für cci.system.audit_log — Format-Symmetrie zu ccc/cca."""

from __future__ import annotations

import logging
import re

import pytest

from cci.system.audit_log import init_audit_log

ISO_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z \[\w+\] ")


@pytest.fixture(autouse=True)
def cleanup_loggers():
    """Räume Test-Logger nach jedem Case (verhindert Handler-Leak)."""
    yield
    for name in list(logging.Logger.manager.loggerDict):
        logger = logging.getLogger(name)
        for h in list(logger.handlers):
            h.close()
            logger.removeHandler(h)


# Case 1: init_audit_log schreibt INIT-Boundary-Marker im ISO-Format
def test_init_writes_boundary_marker(tmp_path):
    log_file = tmp_path / "audit.log"
    init_audit_log(path=log_file, namespace="test_init")
    content = log_file.read_text()
    assert "[INIT] test_init run start" in content
    first_line = content.splitlines()[0]
    assert ISO_PATTERN.match(first_line), (
        f"first line nicht im ISO-Format: {first_line!r}"
    )


# Case 2: Logger-Records werden im Bash-kompatiblen Format geschrieben
def test_logger_format_matches_bash(tmp_path):
    log_file = tmp_path / "audit.log"
    logger = init_audit_log(path=log_file, namespace="test_format")
    logger.info("hello cci")
    logger.error("boom")
    lines = log_file.read_text().splitlines()
    info_line = next(line for line in lines if "hello cci" in line)
    error_line = next(line for line in lines if "boom" in line)
    assert info_line.endswith("[INFO] hello cci")
    assert error_line.endswith("[ERROR] boom")
    assert ISO_PATTERN.match(info_line)
    assert ISO_PATTERN.match(error_line)


# Case 3: Re-Init = Append, kein Overwrite + Idempotenz-Schutz
def test_reinit_appends_no_overwrite(tmp_path):
    log_file = tmp_path / "audit.log"
    logger = init_audit_log(path=log_file, namespace="test_reinit")
    logger.info("first run record")
    handler_count_first = len(logger.handlers)

    logger = init_audit_log(path=log_file, namespace="test_reinit")
    logger.info("second run record")

    content = log_file.read_text()
    assert "first run record" in content
    assert "second run record" in content
    # Idempotenz: keine doppelten Handler bei Re-Init
    assert len(logger.handlers) == handler_count_first

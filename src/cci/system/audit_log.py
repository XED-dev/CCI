"""audit_log — minimal Bash↔Python-kompatibel.

Format identisch zu ccc/cca-audit_log:
    '<ISO-UTC> [LEVEL] message'

Ein `grep '\\[LEVEL\\]' /var/log/xed-cci.log` liefert grep-Pipeline-Ergebnis
über Bash- und Python-Layer hinweg (auch wenn cci selbst Python-only ist,
ist das Format für Operator-Symmetrie zur ccc/cca-Audit-Log-Welt nützlich).

Eigene Lib in cci.system, KEIN Import aus `ccc.system.audit_log`
(Cross-Repo-Lib-Trennung per DevOps-Direktive 2026-05-06).

Phase 1 v0.0.1 minimal:
- INIT-Boundary-Marker beim Run-Start
- Standard-INFO/ERROR-Logging via `logger.info()/error()`
- Keine [PHASE]/[VERIFY]-Helper (Single-Verb-Composition braucht's nicht;
  optional in SS5 wenn Bedarf in Live-Test sichtbar wird)
"""

from __future__ import annotations

import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

DEFAULT_PATH = Path("/var/log/xed-cci.log")
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_BACKUP_COUNT = 5
DEFAULT_NAMESPACE = "xed.cci"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def init_audit_log(
    path: Optional[Path] = None,
    namespace: str = DEFAULT_NAMESPACE,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> logging.Logger:
    """Initialize cci-Audit-Logger mit RotatingFileHandler.

    Bündelt: mkdir parents + RotatingFileHandler + ISO-UTC-Formatter +
    UTC-Converter (statt localtime) + Run-Boundary-Header.

    Idempotent: zweiter Aufruf erkennt existierenden Handler an Marker-
    Attribut und überspringt Re-Init. Kein doppelter Handler, kein
    doppeltes Logging.

    Args:
        path: Log-Datei-Pfad (Default: /var/log/xed-cci.log).
        namespace: Logger-Namespace (Default: 'xed.cci').
        max_bytes: Rotations-Größe (Default 10 MB).
        backup_count: Backup-Anzahl (Default 5).

    Returns:
        Initialisierter Logger mit RotatingFileHandler + INIT-Marker.
    """
    logging.Formatter.converter = time.gmtime  # UTC global

    log_path = path or DEFAULT_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(namespace)

    if any(getattr(h, "_xed_audit", False) for h in logger.handlers):
        return logger

    handler = RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    handler._xed_audit = True  # noqa: SLF001
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("[INIT] %s run start", namespace)
    return logger

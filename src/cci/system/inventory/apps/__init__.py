"""apps — App-Detection-Registry für Server-Installationen.

Phase 1 v0.0.1: Typo3-Detector. Weitere Detector (WordPress, Ghost,
Drupal, Joomla, Laravel) als Backlog für v0.x.

Senior-Pre-Hint H5 (AI039 SS4 2026-05-08): Mainstream-Map-Pattern
statt pluggy. pluggy ab v0.1.0 wenn Anzahl Apps > 5 (Lakmus-Test analog
Cement-Erwägung in ccc/cca).

Format-Spec: WHITEPAPER §JSON-Output-Schema §apps ist Liste von
AppInfo-Records über alle DETECTORS.
"""

from __future__ import annotations

from typing import Callable

from cci.system.inventory.apps._types import AppInfo
from cci.system.inventory.apps.typo3 import detect_typo3

# DETECTORS-Registry: Mainstream-Map (kein pluggy in v0.0.1)
DETECTORS: dict[str, Callable[[], list[AppInfo]]] = {
    "typo3": detect_typo3,
}


def collect_apps_info() -> list[AppInfo]:
    """Composition über alle DETECTORS.

    Iteriert über alle registrierten Detector-Funktionen + bündelt
    Ergebnisse in eine Liste. Pro Detector-Funktion können 0..n
    AppInfo-Records zurückkommen (z.B. eine Box mit drei TYPO3-Sites
    liefert drei Records).

    Returns:
        Liste von AppInfo-Records über alle erkannten Server-Apps
        (leer wenn keine).
    """
    apps: list[AppInfo] = []
    for detector in DETECTORS.values():
        apps.extend(detector())
    return apps


__all__ = ["AppInfo", "DETECTORS", "collect_apps_info", "detect_typo3"]

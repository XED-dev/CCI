"""Type-Definitionen für App-Detection-Registry."""

from __future__ import annotations

from typing import Literal, TypedDict


AppMode = Literal["composer", "classic"]


class AppInfo(TypedDict):
    """Server-App-Inventur-Eintrag matching WHITEPAPER §JSON-Schema §apps."""

    name: str
    version: str
    path: str
    config_file: str
    mode: AppMode


TYPO3DetectionSource = Literal[
    "vendor-php",     # vendor/typo3/cms-core/Classes/Information/Typo3Version.php
    "composer-lock",  # composer.lock packages[] mit typo3/cms-core
    "composer-json",  # composer.json require mit typo3/cms-core OR typo3/cms-*
    "typo3conf-php",  # Classic-Mode typo3conf/LocalConfiguration.php (Legacy)
]


class TYPO3DetectionResult(TypedDict):
    """Detection-Output von _detect_typo3_project (v0.0.10).

    Multi-Source-Detection-Hierarchie liefert Pure-Function-Result pro
    Project-Root. `version` ist `'unknown'` wenn nur composer.json
    erreichbar (Constraint statt resolved Version). `source` markiert
    welche Quelle die Detection ausgelöst hat (für Diagnose +
    Schema-Drift-Erkennung in v0.0.11).
    """

    version: str
    source: TYPO3DetectionSource
    config_file: str
    mode: AppMode

"""typo3 — App-Detector für TYPO3-Installationen unter /var/www/.

Stdlib-only via pathlib + json:
- `Path.glob()` für Scan unter /var/www/ (KEIN subprocess find)
- `Path.read_text()` für Konfig + Version-Files (KEIN subprocess cat)
- `json.loads()` für composer.json + composer.lock-Parse
- `Path.exists()/is_dir()` für Detection

Strukturell noch Read-Only-er als safe_run-subprocess: kein Whitelist-
Bypass möglich, weil keine subprocess-Calls.

Detection-Strategie — zwei TYPO3-Layout-Klassen:

1. **Composer-Mode (TYPO3 v11+ Standard):** Project-Root mit
   `composer.json` (mit `typo3/cms-core` in `require`), Vendor in
   `vendor/typo3/cms-core/`, Web-Root in `<site>/public/` (Default;
   via `extra.typo3/cms.web-dir` customizable).
   Layout verifiziert via WebFetch docs.typo3.org 2026-05-12.

2. **Classic-Mode (TYPO3 ≤ v10 + Legacy v11):** Web-Root mit
   `typo3conf/LocalConfiguration.php`, Code-Verzeichnis direkt im
   Web-Root (`typo3/sysext/core/`).

Typo3Version.php-Format (verifiziert via WebFetch 2026-05-08):
`(public|protected|private)? const VERSION = 'X.Y.Z[-suffix]'`.
Beispiele aus TYPO3-Releases:
- v9-v11: `public const VERSION = '11.5.0';`
- v12+: `protected const VERSION = '12.4.10';`
- main-Branch: `protected const VERSION = '15.0.0-dev';`
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from cci.system.inventory.apps._types import AppInfo


# Standard-Suchpfad für TYPO3-Installationen
_VAR_WWW = Path("/var/www")

# Composer-Mode (TYPO3 v11+): composer.json an Project-Root
_COMPOSER_JSON_GLOB = "*/composer.json"
_TYPO3_PACKAGE = "typo3/cms-core"
_VENDOR_VERSION_REL_PATH = (
    "vendor/typo3/cms-core/Classes/Information/Typo3Version.php"
)
_COMPOSER_LOCK_NAME = "composer.lock"

# Classic-Mode (TYPO3 ≤ v10 + Legacy v11): LocalConfiguration.php-Marker
# - htdocs/-Layout (häufig bei nginx/apache mit DocumentRoot in htdocs/)
# - flat-Layout (typo3conf direkt unter Site-Root)
_CONFIG_GLOB_HTDOCS = "*/htdocs/typo3conf/LocalConfiguration.php"
_CONFIG_GLOB_FLAT = "*/typo3conf/LocalConfiguration.php"

# Typo3Version.php-Pfad relativ zum Classic-Mode-Web-Root (= Parent von typo3conf/)
_VERSION_REL_PATH = "typo3/sysext/core/Classes/Information/Typo3Version.php"

# Regex: matcht 'const VERSION = ...' mit optionalem Visibility-Modifier
# (protected/public/private). Wert in einfachen oder doppelten Quotes.
_VERSION_PATTERN = re.compile(
    r"const\s+VERSION\s*=\s*['\"]([^'\"]+)['\"]"
)

_UNKNOWN = "unknown"


def _parse_typo3_version(version_php: Path) -> str:
    """Parst VERSION-Konstante aus Typo3Version.php.

    Returns:
        Versions-String (z.B. '12.4.10' oder '15.0.0-dev') oder
        '_UNKNOWN' wenn File nicht lesbar oder Pattern nicht matcht.
    """
    try:
        content = version_php.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return _UNKNOWN
    match = _VERSION_PATTERN.search(content)
    return match.group(1) if match else _UNKNOWN


def _is_typo3_composer_project(composer_json: Path) -> bool:
    """Check ob composer.json eine TYPO3-Site identifiziert.

    Sucht `typo3/cms-core` in `require` (Production-Dependency).
    Defensive: bei OSError/JSONDecodeError/Schema-Drift → False (kein Crash).
    """
    try:
        data = json.loads(composer_json.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    require = data.get("require", {}) if isinstance(data, dict) else {}
    if not isinstance(require, dict):
        return False
    return _TYPO3_PACKAGE in require


def _parse_typo3_version_from_lockfile(composer_lock: Path) -> str:
    """Fallback-Version-Extraktion aus composer.lock.

    Sucht in `packages[]` nach `{"name": "typo3/cms-core", "version": "..."}`.
    Returnt Version-String (mit ggf. führendem 'v' entfernt) oder _UNKNOWN.
    Defensive: bei OSError/JSONDecodeError/Schema-Drift → _UNKNOWN.
    """
    try:
        data = json.loads(composer_lock.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _UNKNOWN
    if not isinstance(data, dict):
        return _UNKNOWN
    packages = data.get("packages", [])
    if not isinstance(packages, list):
        return _UNKNOWN
    for pkg in packages:
        if not isinstance(pkg, dict):
            continue
        if pkg.get("name") != _TYPO3_PACKAGE:
            continue
        version = pkg.get("version")
        if isinstance(version, str):
            # composer.lock kann 'v13.4.1' oder '13.4.1' speichern — Prefix-trim
            return version.lstrip("v")
    return _UNKNOWN


def _detect_composer_mode_sites(seen: set[Path]) -> list[AppInfo]:
    """Composer-Mode-TYPO3-Detection (TYPO3 v11+ Project-Layout).

    Scannt `<var_www>/*/composer.json`, filtert auf `typo3/cms-core`-
    Dependency, extrahiert Version aus `vendor/.../Typo3Version.php`
    oder Fallback aus `composer.lock`.

    `seen`-Set wird mutiert (Caller teilt mit Classic-Mode-Detection).

    Returns:
        Liste von AppInfo (kann leer sein).
    """
    apps: list[AppInfo] = []
    try:
        composer_jsons = list(_VAR_WWW.glob(_COMPOSER_JSON_GLOB))
    except (PermissionError, OSError):
        return apps

    for composer_json in composer_jsons:
        if not _is_typo3_composer_project(composer_json):
            continue
        web_root = composer_json.parent
        if web_root in seen:
            continue
        seen.add(web_root)

        # Version-Extraktion: vendor zuerst, composer.lock als Fallback
        vendor_version_php = web_root / _VENDOR_VERSION_REL_PATH
        version = _parse_typo3_version(vendor_version_php)
        if version == _UNKNOWN:
            version = _parse_typo3_version_from_lockfile(
                web_root / _COMPOSER_LOCK_NAME
            )

        apps.append(
            AppInfo(
                name="typo3",
                version=version,
                path=str(web_root),
                config_file="composer.json",
                mode="composer",
            )
        )
    return apps


def _detect_classic_mode_sites(seen: set[Path]) -> list[AppInfo]:
    """Classic-Mode-TYPO3-Detection (typo3conf/LocalConfiguration.php).

    Scannt htdocs- und flat-Layout. `seen`-Set wird mutiert (Caller teilt
    mit Composer-Mode-Detection).

    Returns:
        Liste von AppInfo (kann leer sein).
    """
    apps: list[AppInfo] = []
    for pattern in (_CONFIG_GLOB_HTDOCS, _CONFIG_GLOB_FLAT):
        try:
            matches = list(_VAR_WWW.glob(pattern))
        except (PermissionError, OSError):
            continue
        for config_file in matches:
            web_root = config_file.parent.parent  # parent of typo3conf/
            if web_root in seen:
                continue
            seen.add(web_root)
            version_php = web_root / _VERSION_REL_PATH
            apps.append(
                AppInfo(
                    name="typo3",
                    version=_parse_typo3_version(version_php),
                    path=str(web_root),
                    config_file=str(config_file.relative_to(web_root)),
                    mode="classic",
                )
            )
    return apps


def detect_typo3() -> list[AppInfo]:
    """Scant /var/www/ nach TYPO3-Installationen.

    Zwei-Phasen-Detection:
    1. Composer-Mode (TYPO3 v11+): composer.json mit typo3/cms-core-Dependency
    2. Classic-Mode (TYPO3 ≤ v10 + Legacy v11): typo3conf/LocalConfiguration.php

    `seen`-Set verhindert Doppel-Detection (z.B. Site die sowohl composer.json
    als auch typo3conf/LocalConfiguration.php hat). Composer-Mode hat Vorrang
    (moderner Layout).

    Bei nicht-existentem `/var/www/`: leere Liste.
    Bei PermissionError beim Glob: leere Liste (defensive — kein Crash).

    Returns:
        Liste von AppInfo-Records (leer wenn keine TYPO3-Installation).
    """
    if not _VAR_WWW.exists() or not _VAR_WWW.is_dir():
        return []

    seen: set[Path] = set()
    apps = _detect_composer_mode_sites(seen)
    apps.extend(_detect_classic_mode_sites(seen))
    return apps

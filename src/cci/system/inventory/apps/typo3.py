"""typo3 — App-Detector für TYPO3-Installationen unter /var/www/.

Stdlib-only via pathlib (Senior-Pre-Hint H3 AI039 SS4 2026-05-08):
- `Path.glob()` für Scan unter /var/www/ (KEIN subprocess find)
- `Path.read_text()` für Konfig + Version-Files (KEIN subprocess cat)
- `Path.exists()/is_dir()` für Detection

Strukturell noch Read-Only-er als safe_run-subprocess: kein Whitelist-
Bypass möglich, weil keine subprocess-Calls.

Typo3Version.php-Format (Tool-CLI-Help-First-verifiziert via WebFetch
2026-05-08): `(public|protected|private)? const VERSION = 'X.Y.Z[-suffix]'`.
Beispiele aus TYPO3-Releases:
- v9-v11: `public const VERSION = '11.5.0';`
- v12+: `protected const VERSION = '12.4.10';`
- main-Branch: `protected const VERSION = '15.0.0-dev';`
"""

from __future__ import annotations

import re
from pathlib import Path

from cci.system.inventory.apps._types import AppInfo


# Standard-Suchpfad für TYPO3-Installationen
_VAR_WWW = Path("/var/www")

# Glob-Pattern für LocalConfiguration.php-Marker:
# - htdocs/-Layout (häufig bei nginx/apache mit DocumentRoot in htdocs/)
# - flat-Layout (typo3conf direkt unter Site-Root)
_CONFIG_GLOB_HTDOCS = "*/htdocs/typo3conf/LocalConfiguration.php"
_CONFIG_GLOB_FLAT = "*/typo3conf/LocalConfiguration.php"

# Typo3Version.php-Pfad relativ zum Web-Root (= Parent von typo3conf/)
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


def detect_typo3() -> list[AppInfo]:
    """Scant /var/www/ nach TYPO3-Installationen.

    Detection-Marker: `typo3conf/LocalConfiguration.php` unter
    `*/htdocs/` oder direkt `*/`. Pro Match wird Web-Root identifiziert
    + Version aus `typo3/sysext/core/Classes/Information/Typo3Version.php`
    geparst.

    Bei nicht-existentem `/var/www/`: leere Liste.
    Bei PermissionError beim Glob: leere Liste (defensive — kein Crash).

    Returns:
        Liste von AppInfo-Records (leer wenn keine TYPO3-Installation).
    """
    apps: list[AppInfo] = []
    if not _VAR_WWW.exists() or not _VAR_WWW.is_dir():
        return apps

    seen: set[Path] = set()
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
                )
            )
    return apps

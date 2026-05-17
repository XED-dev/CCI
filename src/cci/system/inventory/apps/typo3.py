"""typo3 — App-Detector für TYPO3-Installationen unter /var/www/.

Stdlib-only via pathlib + json:
- `Path.glob()` für Scan unter /var/www/ (KEIN subprocess find)
- `Path.read_text()` für Konfig + Version-Files (KEIN subprocess cat)
- `json.loads()` für composer.json + composer.lock-Parse
- `Path.exists()/is_dir()` für Detection

Strukturell noch Read-Only-er als safe_run-subprocess: kein Whitelist-
Bypass möglich, weil keine subprocess-Calls.

Detection-Strategie — zwei TYPO3-Layout-Klassen (Composer hat 4 Layouts):

1. **Composer-Mode (TYPO3 v11+ Standard):** Project-Root mit
   `composer.json` (mit `typo3/cms-core` in `require`), Vendor in
   `vendor/typo3/cms-core/`. Vier Layouts:

   a) **Top-Level:** `<site>/composer.json` — Mainstream-Composer-Mode
   b) **Deployer-Style:** `<site>/current/composer.json` — atomic
      release-Symlink (deployer.org-Pattern, TYPO3-Standard für CI/CD)
   c) **typo3-base:** `typo3/<site>/composer.json` — DevOps-Konvention
      auf WordOps-Boxen (Site-Trennung von WordOps-Default-Layout)
   d) **Kombiniert:** `typo3/<site>/current/composer.json` — typo3-base
      + Deployer-Layout

   v0.0.9-Refactor: `pathlib.Path.glob()` ersetzt durch explizite Pfad-
   Auswertung via `iterdir()` + `is_file()` / `is_dir()`. Wurzel: Python
   3.10 `glob()` ist mit intermediate relativem Symlink (deployer.org
   `current → releases/<N>/`) unzuverlässig — Live-Failure auf osU2404
   trotz pytest grün (Tests nutzten absolute Symlinks via `symlink_to(
   target, target_is_directory=True)` und reproduzierten die Live-
   Bedingung nicht). `is_file()` folgt Symlinks deterministisch (relativ
   + absolut), `iterdir()` listet Dir-Einträge ohne Glob-Semantik.

   Layout verifiziert via WebFetch docs.typo3.org 2026-05-12 + deployer.org
   TYPO3-Recipe 2026-05-13. Site-Root-Resolution strippt „current/"
   Komponente bei Deployer (logischer Site-Root ist Parent von current/).

2. **Classic-Mode (TYPO3 ≤ v10 + Legacy v11):** Web-Root mit
   `typo3conf/LocalConfiguration.php`, Code-Verzeichnis direkt im
   Web-Root (`typo3/sysext/core/`).

Typo3Version.php-Format (verifiziert via WebFetch 2026-05-08):
`(public|protected|private)? const VERSION = 'X.Y.Z[-suffix]'`.
Beispiele aus TYPO3-Releases:
- v9-v11: `public const VERSION = '11.5.0';`
- v12+: `protected const VERSION = '12.4.10';`
- main-Branch: `protected const VERSION = '15.0.0-dev';`

---

v0.0.10 — Detection-Multi-Source-Hierarchie:

Die neue Public-API `_detect_typo3_project(project_root: Path)` ist
eine Pure Detection Function (kein Filesystem-Scan, kein /var/www-
iterdir). Pro Project-Root wird mit folgender Hierarchie geprüft —
erste positive Source gewinnt:

  1. **vendor-php** (autoritativ, lokal installiert) —
     `vendor/typo3/cms-core/Classes/Information/Typo3Version.php` mit
     parsable VERSION-Konstante. Beweis dass TYPO3-Composer-Install
     gelaufen ist + welche echte Version installiert wurde.
  2. **composer-lock** (transitive Detection) — `composer.lock`
     `packages[]` mit `name == typo3/cms-core` + `version`. Erfasst
     Custom-Distribution-Wrappers (z.B. `mmcagentur/...`) die TYPO3
     transitiv via eigene Meta-Pakete bündeln.
  3. **composer-json** (Custom-Wrapper-Fallback) — `composer.json`
     `require` mit `typo3/cms-core` ODER irgendein `typo3/cms-*`-
     Package. Version-Constraint statt resolved Version, daher
     `version=unknown` als Detection-Result.

Live-Asche v0.0.9: meine alte Detection prüfte nur direkter
`typo3/cms-core` in `require` (Source 3 strikt) — verfehlte
mmcagentur-Custom-Wrapper-Sites, die `typo3/cms-core` nur transitive
in composer.lock haben (Source 2).

Site-Enumeration (welche project_roots geprüft werden) wandert in
v0.0.10 zu `cci/system/inventory/sites.py` (Werkzeug-First via
`wo site list` + Nginx-Config-Parse). `_detect_typo3_project` ist
pure: bekommt project_root als Input, prüft drei Sources, returnt
Result.

Backwards-Compat: `detect_typo3()` legacy bleibt — ruft intern
`_detect_typo3_project` pro `/var/www/<site>/`-iterdir-Kandidat auf,
für Tests die noch das legacy-API nutzen.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from cci.system.inventory.apps._types import AppInfo, TYPO3DetectionResult


# Standard-Suchpfad für TYPO3-Installationen
_VAR_WWW = Path("/var/www")

# Composer-Mode (TYPO3 v11+): composer.json an Project-Root.
# v0.0.9-Refactor: vier Layout-Patterns werden via expliziter Pfad-Tests
# pro Site-Verzeichnis ausgewertet (siehe _scan_site_for_typo3 + _detect_
# composer_mode_sites unten) statt via _VAR_WWW.glob() — Letzteres ist in
# Python 3.10 mit relativem intermediate Symlink (current → releases/<N>)
# unzuverlässig.
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

    v0.0.10 — OR-Logic gegen Custom-Distribution-Wrapper:
    matched `typo3/cms-core` ODER irgendein `typo3/cms-*`-Package in
    `require`. Hintergrund: Custom-Distribution-Projects (z.B.
    `mmcagentur/typo3-website-...`) bündeln eigene Meta-Packages und
    ziehen `typo3/cms-core` oft nur transitive via composer.lock,
    während require direkt nur Custom-Wrapper-Pakete oder einzelne
    `typo3/cms-backend`/`-frontend`/`-extbase`-Packages listet.

    Defensive: bei OSError/JSONDecodeError/Schema-Drift → False
    (kein Crash).
    """
    try:
        data = json.loads(composer_json.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    require = data.get("require", {}) if isinstance(data, dict) else {}
    if not isinstance(require, dict):
        return False
    for pkg_name in require:
        if pkg_name == _TYPO3_PACKAGE:
            return True
        if isinstance(pkg_name, str) and pkg_name.startswith("typo3/cms-"):
            return True
    return False


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


def _resolve_site_root(composer_json: Path) -> Path:
    """Resolve logical site-root from composer.json path.

    Bei Deployer-Layout (composer.json in `current/`) ist `current/`
    ein Symlink auf `releases/<N>/`. Der logische Site-Root ist Parent
    von `current/`, NICHT `current/` selbst — sonst zeigt path-Field
    auf flüchtigen release-Pfad statt Site-Identität.

    Bei anderen Layouts (Top-Level, typo3-base ohne Deployer):
    `composer_json.parent` IST bereits logischer Site-Root.

    Returns:
        Path zum logischen Site-Root.
    """
    parent = composer_json.parent
    if parent.name == "current":
        return parent.parent
    return parent


def _safe_is_file(path: Path) -> bool:
    """`is_file()` defensive — PermissionError/OSError → False.

    Pfad-Tests in Live-Use treffen Verzeichnisse mit beschränkten
    Read-Permissions (z.B. Workstation-`/var/www/html/` für non-www-data-
    User, oder Box-spezifische ACLs). `is_file()` wirft dann
    PermissionError beim `stat()`-Aufruf. Default zu False = „nicht
    sichtbar / nicht zugänglich" entspricht der Read-Only-Inventur-
    Semantik (cci sieht nur was es lesen darf).
    """
    try:
        return path.is_file()
    except (PermissionError, OSError):
        return False


def _safe_is_dir(path: Path) -> bool:
    """`is_dir()` defensive — analog zu `_safe_is_file`."""
    try:
        return path.is_dir()
    except (PermissionError, OSError):
        return False


def _detect_typo3_project(project_root: Path) -> Optional[TYPO3DetectionResult]:
    """Pure-Detection: ob `project_root` eine TYPO3-Installation ist (v0.0.10).

    Multi-Source-Hierarchie — erste positive Source gewinnt:
      1. vendor-php (autoritativ, installed): `vendor/typo3/cms-core/Classes/
         Information/Typo3Version.php` — Version aus PHP-Const-Parse.
      2. composer-lock (transitive): `composer.lock` `packages[]` mit
         `name == typo3/cms-core` — Version aus lock-File. Erfasst Custom-
         Distribution-Wrappers (mmcagentur-Style) die TYPO3 nur transitive
         in require haben.
      3. composer-json (Fallback): `composer.json` `require` mit
         `typo3/cms-core` ODER irgendein `typo3/cms-*`-Package. Nur
         Constraint statt resolved Version → `version=unknown`.

    Pure Function: kein Filesystem-Scan, kein subprocess. Site-Enumeration
    (welche project_roots geprüft werden) ist Aufgabe des Callers
    (`sites.py` ab v0.0.10 / `detect_typo3` legacy für `/var/www/`-iterdir).

    Defensive: bei keiner positiven Source returns None. Permission-Fehler
    werden via `_safe_is_file` abgefangen (returns False → Source-Skip).

    Args:
        project_root: Path zum Project-Root (z.B. `/var/www/<site>/current/`).

    Returns:
        `TYPO3DetectionResult` wenn TYPO3 erkannt, sonst None.
    """
    # Source 1: vendor-php (autoritativ, installed-Version)
    vendor_php = project_root / _VENDOR_VERSION_REL_PATH
    if _safe_is_file(vendor_php):
        version = _parse_typo3_version(vendor_php)
        # vendor existiert → TYPO3 ist installiert. Wenn VERSION-Parse
        # _UNKNOWN ergibt (Partial-Install ohne parsable VERSION-Konst),
        # versuche Fallback zu composer-lock für echte Version.
        if version == _UNKNOWN:
            composer_lock_fallback = project_root / _COMPOSER_LOCK_NAME
            if _safe_is_file(composer_lock_fallback):
                lock_version = _parse_typo3_version_from_lockfile(
                    composer_lock_fallback
                )
                if lock_version != _UNKNOWN:
                    version = lock_version
        return TYPO3DetectionResult(
            version=version,
            source="vendor-php",
            config_file="composer.json",
            mode="composer",
        )

    # Source 2: composer-lock (transitive Detection ohne vendor-Install)
    composer_lock = project_root / _COMPOSER_LOCK_NAME
    if _safe_is_file(composer_lock):
        version = _parse_typo3_version_from_lockfile(composer_lock)
        if version != _UNKNOWN:
            return TYPO3DetectionResult(
                version=version,
                source="composer-lock",
                config_file="composer.json",
                mode="composer",
            )

    # Source 3: composer-json (Custom-Wrapper-Fallback, OR-Logic)
    composer_json = project_root / "composer.json"
    if _safe_is_file(composer_json) and _is_typo3_composer_project(composer_json):
        return TYPO3DetectionResult(
            version=_UNKNOWN,
            source="composer-json",
            config_file="composer.json",
            mode="composer",
        )

    return None


def _check_composer_candidate(
    composer_json: Path, seen: set[Path], apps: list[AppInfo]
) -> None:
    """Auswerte composer.json wenn es ein TYPO3-Project ist und hänge AppInfo an apps.

    `is_file()` folgt Symlinks deterministisch in Python 3.10+ (auch
    relative intermediate Symlinks wie deployer.org `current →
    releases/<N>/`). Bei dangling Symlink oder Nicht-Existenz: kein-op,
    kein Crash.

    Dedup via `seen`-Set auf logischem site_root (Top-Level + Deployer
    referenzieren denselben Site-Root → nur ein AppInfo). `seen` wird
    mutiert; Caller teilt das Set mit Classic-Mode-Detection.

    Args:
        composer_json: Kandidat-Pfad (existiert ggf. nicht; is_file()-Check
            entscheidet).
        seen: Set bereits erfasster Site-Roots (mutiert).
        apps: AppInfo-Liste (mutiert via append).
    """
    if not _safe_is_file(composer_json):
        return
    if not _is_typo3_composer_project(composer_json):
        return
    site_root = _resolve_site_root(composer_json)
    if site_root in seen:
        return
    seen.add(site_root)

    # web_root: composer.json.parent = Code-Verzeichnis. Bei Deployer-
    # Layout ist das `<site>/current/` (Symlink auf releases/<N>/) —
    # Path-Operationen wie `web_root / vendor/...` folgen dem Symlink
    # transparent.
    web_root = composer_json.parent

    # Version-Extraktion: vendor zuerst, composer.lock als Fallback.
    vendor_version_php = web_root / _VENDOR_VERSION_REL_PATH
    version = _parse_typo3_version(vendor_version_php)
    if version == _UNKNOWN:
        version = _parse_typo3_version_from_lockfile(
            web_root / _COMPOSER_LOCK_NAME
        )

    # config_file als relativer Pfad zu site_root — zeigt Layout-Pattern
    # implizit ohne extra Schema-Feld:
    #   „composer.json"          → Top-Level
    #   „current/composer.json"  → Deployer (typo3-base via path-Prefix `typo3/`)
    try:
        config_file_rel = str(composer_json.relative_to(site_root))
    except ValueError:
        config_file_rel = "composer.json"

    apps.append(
        AppInfo(
            name="typo3",
            version=version,
            path=str(site_root),
            config_file=config_file_rel,
            mode="composer",
        )
    )


def _scan_site_for_typo3(
    site_dir: Path, seen: set[Path], apps: list[AppInfo]
) -> None:
    """Top-Level + Deployer-Layout pro Site-Verzeichnis prüfen.

    Zwei explizite Pfad-Tests:
    - `<site>/composer.json` — Mainstream-Composer-Mode
    - `<site>/current/composer.json` — Deployer-Pattern (current/ kann
      relativer oder absoluter Symlink sein; is_file() folgt beide)

    Dedup durch `seen` in `_check_composer_candidate`.
    """
    _check_composer_candidate(site_dir / "composer.json", seen, apps)
    _check_composer_candidate(
        site_dir / "current" / "composer.json", seen, apps
    )


def _detect_composer_mode_sites(seen: set[Path]) -> list[AppInfo]:
    """Composer-Mode-TYPO3-Detection via expliziter Pfad-Auswertung.

    Zwei Iterations-Ebenen:
    1. Direkte Sites unter `/var/www/<site>/` — Mainstream + Deployer
    2. typo3-base-Konvention `/var/www/typo3/<site>/` — DevOps-WordOps-
       Pattern (Site-Trennung von WordOps-Default-Layout), kombiniert
       mit Deployer möglich

    Wurzel-Fix v0.0.9: `iterdir()` + `is_dir()` / `is_file()` statt
    `pathlib.Path.glob()`. Python 3.10 `glob()` mit Pattern wie
    `*/current/composer.json` behandelt relative intermediate Symlinks
    inkonsistent — Live-Failure auf osU2404 trotz pytest grün.
    Pfad-Auswertung via `is_file()` folgt Symlinks deterministisch.

    `seen`-Set wird mutiert (Caller teilt mit Classic-Mode-Detection).

    Returns:
        Liste von AppInfo (kann leer sein).
    """
    apps: list[AppInfo] = []
    try:
        site_dirs = list(_VAR_WWW.iterdir())
    except (PermissionError, OSError):
        return apps

    for site_dir in site_dirs:
        if not _safe_is_dir(site_dir):
            continue
        # Ebene 1: Mainstream + Deployer für direkte Sites
        _scan_site_for_typo3(site_dir, seen, apps)
        # Ebene 2: typo3-base-Konvention /var/www/typo3/<sub-site>/
        if site_dir.name == "typo3":
            try:
                sub_dirs = list(site_dir.iterdir())
            except (PermissionError, OSError):
                continue
            for sub_site in sub_dirs:
                if _safe_is_dir(sub_site):
                    _scan_site_for_typo3(sub_site, seen, apps)
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

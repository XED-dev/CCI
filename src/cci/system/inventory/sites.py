"""sites — Werkzeug-First-Site-Enumeration für TYPO3-Box-Klasse (v0.0.10).

Site-Enumeration via WordOps-CLI (`wo site list`) als Primärquelle +
Nginx-Config-Parsing pro Domain für Webroot + PHP-Version. Plus
Webroot-Gruppierung pro unique Webroot (Multi-Webroot-Mapping) und
TYPO3-Detection via `_detect_typo3_project` aus `apps/typo3.py`.

Wurzel-Fix v0.0.10: ersetzt `/var/www/`-iterdir-Heuristik der legacy
`detect_typo3()` durch Werkzeug-First-Enumeration. Live-Asche v0.0.9
auf osU2404 (sites:(none) trotz 9 echte Sites): iterdir-Approach
verfehlt Custom-Site-Dirs (22222, html, typo3-leer) und Multi-Webroot-
Mapping (3 Sites teilen denselben Code-Webroot mit unterschiedlichen
PHP-Versionen).

WordOps `wo site info` ist NICHT autoritativ für PHP-Version (zeigt
WordOps-Internal-Config, nicht aktuelle Nginx-Edit). Autoritativ
ist `/etc/nginx/sites-available/<domain>` mit `include common/php<XY>.conf`
— bestätigt durch Live-Output 2026-05-17 (preprod.scheucherparkett.com
hat `wo site info` PHP 7.4 aber Nginx `include common/php74.conf`,
während scheucherparkett.at gleichen Webroot teilt mit
`include common/php83.conf`).

DevOps-Vote v0.0.10 (b): Webroot ist Quelle der Wahrheit, Domain ist
View darauf. SiteEntry pro unique Webroot mit Domains+PHP als Attribute.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional, TypedDict

from cci.system.inventory.apps.typo3 import _detect_typo3_project
from cci.system.safe_run import ReadOnlyViolationError, safe_run

# Standard-Pfad zu Nginx-Site-Configs auf WordOps-LEMP-Boxen
_NGINX_SITES_DIR = Path("/etc/nginx/sites-available")

# Regex: matcht `root /pfad;` (mit beliebigem Pfad, ohne Quotes).
# Wird nach Kommentar-Stripping ausgeführt (siehe `_parse_nginx_site_config`).
_NGINX_ROOT_PATTERN = re.compile(
    r"^\s*root\s+(\S+?);", re.MULTILINE
)
# Regex: matcht `include common/php<XY>.conf;` für PHP-Version-Detection.
# XY = zwei-stellige PHP-Version (74, 80, 81, 82, 83, 84).
_NGINX_PHP_PATTERN = re.compile(
    r"^\s*include\s+common/php(\d+)\.conf;", re.MULTILINE
)


class DomainInfo(TypedDict):
    """Domain-Identität die einen Webroot referenziert.

    Eine Domain kann theoretisch mehrere Server-Blöcke haben (z.B. HTTP +
    HTTPS), aber innerhalb eines Sites-File ist typisch der aktive
    `root`-Direktive gleich. PHP-Version pro Domain (durch
    `include common/phpXY.conf`), nicht pro Webroot.
    """

    domain: str               # "preprod.scheucherparkett.com"
    php_version: str          # "7.4" / "8.3" / "unknown"
    nginx_config: str         # absoluter Pfad zu sites-available/<domain>


class SiteEntry(TypedDict):
    """TYPO3-Site-Eintrag pro unique Webroot (v0.0.10).

    Webroot ist Quelle der Wahrheit (DevOps-Vote v0.0.10 b): mehrere
    Domains können denselben Webroot teilen mit unterschiedlichen
    PHP-Versionen. Multi-Webroot-Mapping wird als list[DomainInfo]
    abgebildet.

    `cms="unknown"` markiert Webroots die nicht TYPO3 sind (z.B.
    WordPress-htdocs-Pattern). Sie werden gelistet aber ohne
    TYPO3-spezifische Felder.
    """

    webroot: str              # "/var/www/preprod.scheucherparkett.com/public"
    project_root: str         # Project-Root für Composer-Detection
    cms: str                  # "typo3" oder "unknown"
    cms_version: str          # "12.4.45" / "unknown"
    cms_mode: str             # "composer" / "classic" / "unknown"
    cms_source: str           # "vendor-php" / "composer-lock" / "composer-json" / ""
    config_file: str          # "composer.json" / ""
    domains: list[DomainInfo]


def _list_wordops_sites() -> list[str]:
    """Subprocess `wo site list` → Liste Domain-Namen.

    Defensive: bei Subprocess-Fehler (wo nicht installiert, Timeout,
    Permission, ReadOnly-Violation) → leere Liste. Caller-Konvention:
    leere Liste = keine WordOps-Sites verfügbar; Box-Klassen-Pre-Step
    sollte dann ohnehin Exit ausgelöst haben (Sub-Sprint N).
    """
    try:
        result = safe_run(["wo", "site", "list"], timeout=5.0)
    except (FileNotFoundError, subprocess.TimeoutExpired, ReadOnlyViolationError):
        return []
    if result.returncode != 0:
        return []
    domains: list[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line:
            domains.append(line)
    return domains


def _parse_nginx_site_config(
    config_path: Path,
) -> tuple[Optional[str], Optional[str]]:
    """Pure-Parse: Nginx-Site-Config-File → (webroot, php_version).

    Algorithm:
    1. File lesen (defensive: bei OSError/UnicodeDecodeError → (None, None))
    2. Kommentar-Lines (^\\s*#) entfernen (manuelle DevOps-Notizen
       im Nginx-File wie `# root /var/www/<site>/htdocs;` werden
       ignoriert)
    3. Regex auf erstem aktivem `root`-Direktive + `include common/phpXY.conf`
    4. PHP-Version "74"→"7.4", "83"→"8.3" (zwei-stellig → punktiert)

    Returns:
        (webroot, php_version) — beide Optional[str].
        (None, None) wenn File nicht lesbar oder keine Match.
    """
    try:
        content = config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return (None, None)

    # Kommentar-Lines (^\s*#) entfernen — manuelle DevOps-Notizen
    # im Nginx-File werden so harmless gemacht (z.B. auskommentierte
    # alte `root /var/www/<site>/htdocs;`-Direktiven).
    active_lines = [
        line for line in content.splitlines()
        if not line.lstrip().startswith("#")
    ]
    active_content = "\n".join(active_lines)

    root_match = _NGINX_ROOT_PATTERN.search(active_content)
    php_match = _NGINX_PHP_PATTERN.search(active_content)

    webroot = root_match.group(1) if root_match else None

    php_version: Optional[str] = None
    if php_match:
        php_digits = php_match.group(1)
        # "74" → "7.4", "83" → "8.3", "100" → "10.0" (defensive für Zukunft)
        if len(php_digits) == 2:
            php_version = f"{php_digits[0]}.{php_digits[1]}"
        elif len(php_digits) == 3:
            php_version = f"{php_digits[:2]}.{php_digits[2]}"
        else:
            php_version = php_digits

    return (webroot, php_version)


def _resolve_project_root(webroot: str) -> Path:
    """Ermittle TYPO3-Project-Root aus Webroot.

    Layout-Patterns:
    - Composer-Mode (TYPO3 v11+): Webroot ist `<project>/public/` →
      Project-Root ist Parent
    - Classic-Mode (TYPO3 ≤ v10): Webroot IST Project-Root (`<site>/htdocs/`)

    Plus: bei Deployer-Pattern zeigt Project-Root auf
    `<site>/current/` (Symlink auf `releases/<N>/`). `_detect_typo3_project`
    folgt das transparent via `is_file()`-Symlink-Resolution.
    """
    webroot_path = Path(webroot)
    if webroot_path.name == "public":
        # Composer-Layout: Project-Root ist Parent (vendor/composer.json/.lock liegen dort)
        return webroot_path.parent
    # Classic-Mode / htdocs-Layout: Webroot = Project-Root
    return webroot_path


def _build_domain_info(
    domain: str, php_version: Optional[str], nginx_dir: Path
) -> DomainInfo:
    """Konstruiere DomainInfo aus Domain-Namen + PHP-Version."""
    return DomainInfo(
        domain=domain,
        php_version=php_version if php_version is not None else "unknown",
        nginx_config=str(nginx_dir / domain),
    )


def collect_sites_info() -> list[SiteEntry]:
    """Werkzeug-First-Site-Enumeration + TYPO3-Detection (v0.0.10).

    Algorithm:
    1. `wo site list` → Liste aller WordOps-Domains (Primärquelle)
    2. Pro Domain: parse `/etc/nginx/sites-available/<domain>` →
       (webroot, php_version)
    3. Webroot-Gruppierung: unique Webroots, Domains+PHP-Versionen
       als list[DomainInfo] pro Webroot (DevOps-Vote v0.0.10 b)
    4. Pro unique Webroot: `_resolve_project_root` + `_detect_typo3_project`
       aus apps/typo3.py (Multi-Source-Hierarchie)
    5. SiteEntry mit `cms="typo3"`|"unknown" + nested domains

    Defensive: bei `wo`-Fehler oder leerer Site-Liste → leere Liste.
    Box-Klassen-Pre-Step (Sub-Sprint N) sollte vor `collect_sites_info`
    laufen und bei Box-Mismatch ohnehin Exit machen.

    Returns:
        list[SiteEntry] mit allen erkannten Webroots (TYPO3 + unknown).
        Reihenfolge nicht garantiert (Dict-Iteration).
    """
    domains = _list_wordops_sites()
    if not domains:
        return []

    # Webroot-Map: webroot-Pfad → list[DomainInfo] die ihn referenzieren
    webroot_map: dict[str, list[DomainInfo]] = {}

    for domain in domains:
        config_path = _NGINX_SITES_DIR / domain
        webroot, php_version = _parse_nginx_site_config(config_path)
        if webroot is None:
            # Domain ohne parsbares Nginx-Config — skip
            continue
        domain_info = _build_domain_info(domain, php_version, _NGINX_SITES_DIR)
        webroot_map.setdefault(webroot, []).append(domain_info)

    sites: list[SiteEntry] = []
    for webroot, domain_list in webroot_map.items():
        project_root = _resolve_project_root(webroot)
        detection = _detect_typo3_project(project_root)

        if detection is not None:
            site = SiteEntry(
                webroot=webroot,
                project_root=str(project_root),
                cms="typo3",
                cms_version=detection["version"],
                cms_mode=detection["mode"],
                cms_source=detection["source"],
                config_file=detection["config_file"],
                domains=domain_list,
            )
        else:
            # Non-TYPO3-Webroot (z.B. WordPress-htdocs-Pattern) —
            # gelistet aber ohne TYPO3-spezifische Felder.
            site = SiteEntry(
                webroot=webroot,
                project_root=str(project_root),
                cms="unknown",
                cms_version="unknown",
                cms_mode="unknown",
                cms_source="",
                config_file="",
                domains=domain_list,
            )
        sites.append(site)

    return sites


__all__ = [
    "DomainInfo",
    "SiteEntry",
    "collect_sites_info",
]

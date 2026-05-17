"""Tests für cci.system.inventory.apps.typo3 — TYPO3-Detector + Registry."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cci.system.inventory.apps import (
    DETECTORS,
    collect_apps_info,
)
from cci.system.inventory.apps.typo3 import (
    _detect_typo3_project,
    _is_typo3_composer_project,
    _parse_typo3_version,
    _parse_typo3_version_from_lockfile,
    _resolve_site_root,
    detect_typo3,
)


# ---------------------------------------------------------------------------
# _parse_typo3_version (Classic-Mode + Composer-Vendor Version-Extraktion)
# ---------------------------------------------------------------------------


# Case 1: _parse_typo3_version mit modernem 'protected const' Pattern
def test_parse_typo3_version_protected_const(tmp_path: Path) -> None:
    """Modern TYPO3 (v12+) nutzt 'protected const VERSION'."""
    version_php = tmp_path / "Typo3Version.php"
    version_php.write_text(
        "<?php\n"
        "namespace TYPO3\\CMS\\Core\\Information;\n"
        "class Typo3Version {\n"
        "    protected const VERSION = '15.0.0-dev';\n"
        "}\n",
        encoding="utf-8",
    )
    assert _parse_typo3_version(version_php) == "15.0.0-dev"


# Case 2: _parse_typo3_version mit altem 'public const' Pattern
def test_parse_typo3_version_public_const(tmp_path: Path) -> None:
    """Älteres TYPO3 (v9-v11) nutzt 'public const VERSION'."""
    version_php = tmp_path / "Typo3Version.php"
    version_php.write_text(
        "<?php\nclass Typo3Version {\n"
        '    public const VERSION = "11.5.0";\n'
        "}\n",
        encoding="utf-8",
    )
    assert _parse_typo3_version(version_php) == "11.5.0"


# Case 3: _parse_typo3_version mit nicht-existentem File -> 'unknown'
def test_parse_typo3_version_missing_file(tmp_path: Path) -> None:
    version_php = tmp_path / "DoesNotExist.php"
    assert _parse_typo3_version(version_php) == "unknown"


# Case 4: _parse_typo3_version mit File ohne VERSION-Pattern -> 'unknown'
def test_parse_typo3_version_no_pattern(tmp_path: Path) -> None:
    version_php = tmp_path / "Typo3Version.php"
    version_php.write_text(
        "<?php\nclass Typo3Version { /* no version constant */ }\n",
        encoding="utf-8",
    )
    assert _parse_typo3_version(version_php) == "unknown"


# ---------------------------------------------------------------------------
# _is_typo3_composer_project (Composer-Mode Project-Identifikation)
# ---------------------------------------------------------------------------


# Case 5: composer.json mit typo3/cms-core in require -> True
def test_is_typo3_composer_project_with_dep(tmp_path: Path) -> None:
    composer_json = tmp_path / "composer.json"
    composer_json.write_text(
        '{"require": {"typo3/cms-core": "^13.4", "php": ">=8.2"}}',
        encoding="utf-8",
    )
    assert _is_typo3_composer_project(composer_json) is True


# Case 6: composer.json ohne typo3/cms-core -> False
def test_is_typo3_composer_project_without_dep(tmp_path: Path) -> None:
    composer_json = tmp_path / "composer.json"
    composer_json.write_text(
        '{"require": {"laravel/framework": "^11.0", "php": ">=8.2"}}',
        encoding="utf-8",
    )
    assert _is_typo3_composer_project(composer_json) is False


# Case 7: Invalid JSON -> False (defensive, kein Crash)
def test_is_typo3_composer_project_invalid_json(tmp_path: Path) -> None:
    composer_json = tmp_path / "composer.json"
    composer_json.write_text("not valid json {", encoding="utf-8")
    assert _is_typo3_composer_project(composer_json) is False


# ---------------------------------------------------------------------------
# _parse_typo3_version_from_lockfile (Composer-Mode Fallback)
# ---------------------------------------------------------------------------


# Case 8: composer.lock mit typo3/cms-core-Eintrag -> version
def test_parse_version_from_lockfile_finds_typo3(tmp_path: Path) -> None:
    composer_lock = tmp_path / "composer.lock"
    composer_lock.write_text(
        '{"packages": ['
        '{"name": "typo3/cms-core", "version": "13.4.1"},'
        '{"name": "symfony/console", "version": "6.4.0"}'
        ']}',
        encoding="utf-8",
    )
    assert _parse_typo3_version_from_lockfile(composer_lock) == "13.4.1"


# Case 9: composer.lock mit 'v'-Prefix vor Version -> stripped
def test_parse_version_from_lockfile_strips_v_prefix(tmp_path: Path) -> None:
    composer_lock = tmp_path / "composer.lock"
    composer_lock.write_text(
        '{"packages": [{"name": "typo3/cms-core", "version": "v12.4.10"}]}',
        encoding="utf-8",
    )
    assert _parse_typo3_version_from_lockfile(composer_lock) == "12.4.10"


# Case 10: composer.lock ohne typo3-Eintrag -> 'unknown'
def test_parse_version_from_lockfile_no_match(tmp_path: Path) -> None:
    composer_lock = tmp_path / "composer.lock"
    composer_lock.write_text(
        '{"packages": [{"name": "symfony/console", "version": "6.4.0"}]}',
        encoding="utf-8",
    )
    assert _parse_typo3_version_from_lockfile(composer_lock) == "unknown"


# ---------------------------------------------------------------------------
# detect_typo3 — Composer-Mode Integration
# ---------------------------------------------------------------------------


# Case 11: Composer-Mode mit vendor/cms-core/Typo3Version.php -> version + mode
def test_detect_typo3_composer_mode_vendor(tmp_path: Path) -> None:
    """Composer-Mode-Site mit installiertem vendor/typo3/cms-core."""
    site = tmp_path / "example.com"
    site.mkdir()
    (site / "composer.json").write_text(
        '{"require": {"typo3/cms-core": "^13.4"}}',
        encoding="utf-8",
    )

    vendor_core = site / "vendor" / "typo3" / "cms-core" / "Classes" / "Information"
    vendor_core.mkdir(parents=True)
    (vendor_core / "Typo3Version.php").write_text(
        "<?php\nclass Typo3Version {\n"
        "    protected const VERSION = '13.4.1';\n}\n",
        encoding="utf-8",
    )

    with patch("cci.system.inventory.apps.typo3._VAR_WWW", tmp_path):
        result = detect_typo3()

    assert len(result) == 1
    assert result[0]["name"] == "typo3"
    assert result[0]["version"] == "13.4.1"
    assert result[0]["path"] == str(site)
    assert result[0]["config_file"] == "composer.json"
    assert result[0]["mode"] == "composer"


# Case 12: Composer-Mode ohne vendor/ aber mit composer.lock -> Fallback-Version
def test_detect_typo3_composer_mode_lockfile_fallback(tmp_path: Path) -> None:
    """Composer-Mode ohne vendor/ — Version aus composer.lock."""
    site = tmp_path / "example.com"
    site.mkdir()
    (site / "composer.json").write_text(
        '{"require": {"typo3/cms-core": "^12.4"}}',
        encoding="utf-8",
    )
    (site / "composer.lock").write_text(
        '{"packages": [{"name": "typo3/cms-core", "version": "12.4.10"}]}',
        encoding="utf-8",
    )

    with patch("cci.system.inventory.apps.typo3._VAR_WWW", tmp_path):
        result = detect_typo3()

    assert len(result) == 1
    assert result[0]["version"] == "12.4.10"
    assert result[0]["mode"] == "composer"


# Case 13: Composer-Mode komplett ohne Version-Info -> 'unknown'
def test_detect_typo3_composer_mode_unknown_version(tmp_path: Path) -> None:
    """Composer-Mode: composer.json vorhanden, aber kein vendor/ und kein lock."""
    site = tmp_path / "example.com"
    site.mkdir()
    (site / "composer.json").write_text(
        '{"require": {"typo3/cms-core": "^13.4"}}',
        encoding="utf-8",
    )

    with patch("cci.system.inventory.apps.typo3._VAR_WWW", tmp_path):
        result = detect_typo3()

    assert len(result) == 1
    assert result[0]["version"] == "unknown"
    assert result[0]["mode"] == "composer"


# Case 14: composer.json ohne typo3/cms-core -> skip (kein Treffer)
def test_detect_typo3_skips_non_typo3_composer(tmp_path: Path) -> None:
    """composer.json mit anderer Framework-Dep wird übersprungen."""
    site = tmp_path / "laravel-site"
    site.mkdir()
    (site / "composer.json").write_text(
        '{"require": {"laravel/framework": "^11.0"}}',
        encoding="utf-8",
    )

    with patch("cci.system.inventory.apps.typo3._VAR_WWW", tmp_path):
        result = detect_typo3()

    assert result == []


# ---------------------------------------------------------------------------
# detect_typo3 — Classic-Mode Integration (mit mode-Feld)
# ---------------------------------------------------------------------------


# Case 15: detect_typo3 mit fingiertem htdocs-Layout -> classic-Mode
def test_detect_typo3_finds_htdocs_installation(tmp_path: Path) -> None:
    """Fingiertes /var/www/example.com/htdocs/typo3conf/ + Typo3Version.php."""
    site = tmp_path / "example.com" / "htdocs"
    typo3conf = site / "typo3conf"
    typo3conf.mkdir(parents=True)
    (typo3conf / "LocalConfiguration.php").write_text(
        "<?php\nreturn [];\n", encoding="utf-8"
    )

    typo3_core = site / "typo3" / "sysext" / "core" / "Classes" / "Information"
    typo3_core.mkdir(parents=True)
    (typo3_core / "Typo3Version.php").write_text(
        "<?php\nclass Typo3Version {\n"
        "    protected const VERSION = '12.4.10';\n}\n",
        encoding="utf-8",
    )

    with patch("cci.system.inventory.apps.typo3._VAR_WWW", tmp_path):
        result = detect_typo3()

    assert len(result) == 1
    assert result[0]["name"] == "typo3"
    assert result[0]["version"] == "12.4.10"
    assert result[0]["path"] == str(site)
    assert result[0]["config_file"] == "typo3conf/LocalConfiguration.php"
    assert result[0]["mode"] == "classic"


# Case 16: detect_typo3 mit flat-Layout -> classic-Mode
def test_detect_typo3_finds_flat_installation(tmp_path: Path) -> None:
    """Flat-Layout: /var/www/example.com/typo3conf/ (kein htdocs)."""
    site = tmp_path / "example.com"
    typo3conf = site / "typo3conf"
    typo3conf.mkdir(parents=True)
    (typo3conf / "LocalConfiguration.php").write_text(
        "<?php\nreturn [];\n", encoding="utf-8"
    )

    typo3_core = site / "typo3" / "sysext" / "core" / "Classes" / "Information"
    typo3_core.mkdir(parents=True)
    (typo3_core / "Typo3Version.php").write_text(
        "<?php\nclass Typo3Version {\n"
        "    protected const VERSION = '13.4.0';\n}\n",
        encoding="utf-8",
    )

    with patch("cci.system.inventory.apps.typo3._VAR_WWW", tmp_path):
        result = detect_typo3()

    assert len(result) == 1
    assert result[0]["name"] == "typo3"
    assert result[0]["version"] == "13.4.0"
    assert result[0]["path"] == str(site)
    assert result[0]["mode"] == "classic"


# ---------------------------------------------------------------------------
# detect_typo3 — Multi-Mode (Coverage für seen-Set über beide Phasen)
# ---------------------------------------------------------------------------


# Case 17: Multi-Site mit Classic + Composer parallel -> 2 Treffer
def test_detect_typo3_multimode_classic_and_composer(tmp_path: Path) -> None:
    """Box mit zwei TYPO3-Sites: eine Classic, eine Composer."""
    # Classic-Mode-Site
    classic_site = tmp_path / "legacy.example.com"
    classic_typo3conf = classic_site / "typo3conf"
    classic_typo3conf.mkdir(parents=True)
    (classic_typo3conf / "LocalConfiguration.php").write_text(
        "<?php\nreturn [];\n", encoding="utf-8"
    )
    classic_core = (
        classic_site / "typo3" / "sysext" / "core" / "Classes" / "Information"
    )
    classic_core.mkdir(parents=True)
    (classic_core / "Typo3Version.php").write_text(
        "<?php\nclass Typo3Version {\n"
        "    public const VERSION = '11.5.32';\n}\n",
        encoding="utf-8",
    )

    # Composer-Mode-Site
    composer_site = tmp_path / "modern.example.com"
    composer_site.mkdir()
    (composer_site / "composer.json").write_text(
        '{"require": {"typo3/cms-core": "^13.4"}}',
        encoding="utf-8",
    )
    vendor_core = (
        composer_site / "vendor" / "typo3" / "cms-core" / "Classes" / "Information"
    )
    vendor_core.mkdir(parents=True)
    (vendor_core / "Typo3Version.php").write_text(
        "<?php\nclass Typo3Version {\n"
        "    protected const VERSION = '13.4.1';\n}\n",
        encoding="utf-8",
    )

    with patch("cci.system.inventory.apps.typo3._VAR_WWW", tmp_path):
        result = detect_typo3()

    assert len(result) == 2
    modes = {entry["mode"] for entry in result}
    assert modes == {"classic", "composer"}
    versions = {entry["version"] for entry in result}
    assert versions == {"11.5.32", "13.4.1"}


# ---------------------------------------------------------------------------
# detect_typo3 — Edge-Cases
# ---------------------------------------------------------------------------


# Case 18: detect_typo3 mit nicht-existentem /var/www/ -> leere Liste
def test_detect_typo3_no_var_www(tmp_path: Path) -> None:
    fake_path = tmp_path / "nonexistent"
    with patch("cci.system.inventory.apps.typo3._VAR_WWW", fake_path):
        result = detect_typo3()
    assert result == []


# Case 19: detect_typo3 mit existing /var/www/ aber keinem typo3 -> leere Liste
def test_detect_typo3_no_typo3_installations(tmp_path: Path) -> None:
    """Statisches Site ohne TYPO3-Marker -> 0 Treffer."""
    static_site = tmp_path / "static-site"
    static_site.mkdir()
    (static_site / "index.html").write_text("hello", encoding="utf-8")

    with patch("cci.system.inventory.apps.typo3._VAR_WWW", tmp_path):
        result = detect_typo3()
    assert result == []


# ---------------------------------------------------------------------------
# Registry-Tests
# ---------------------------------------------------------------------------


# Case 20: collect_apps_info nutzt DETECTORS-Registry
def test_collect_apps_info_uses_registry(tmp_path: Path) -> None:
    """collect_apps_info iteriert DETECTORS — leere Box -> leere Liste."""
    fake_path = tmp_path / "nonexistent"
    with patch("cci.system.inventory.apps.typo3._VAR_WWW", fake_path):
        result = collect_apps_info()
    assert isinstance(result, list)
    assert result == []


# Case 21: DETECTORS-Registry enthält erwartete Detector-Funktionen
def test_detectors_registry_contains_typo3() -> None:
    """v0.0.x: nur typo3 in Registry. Lakmus-Test gegen versehentliche
    Pre-Optimization (pluggy/zusätzliche Detectors)."""
    assert "typo3" in DETECTORS
    assert callable(DETECTORS["typo3"])
    # Phase 1 v0.0.x: nur ein Detector — weitere Apps als v0.x-Backlog
    assert len(DETECTORS) == 1


# ---------------------------------------------------------------------------
# _resolve_site_root (v0.0.8 — Deployer-Layout-Support)
# ---------------------------------------------------------------------------


# Case 22: _resolve_site_root strippt 'current/' für Deployer-Layout
def test_resolve_site_root_strips_current() -> None:
    """Deployer-Layout: composer.json in <site>/current/ → site_root = <site>/."""
    composer_json = Path("/var/www/site.com/current/composer.json")
    assert _resolve_site_root(composer_json) == Path("/var/www/site.com")


# Case 23: _resolve_site_root nimmt parent direkt wenn nicht 'current/'
def test_resolve_site_root_keeps_direct() -> None:
    """Top-Level-Layout: composer_json.parent IST site_root."""
    composer_json = Path("/var/www/site.com/composer.json")
    assert _resolve_site_root(composer_json) == Path("/var/www/site.com")


# ---------------------------------------------------------------------------
# detect_typo3 — neue Layout-Sub-Patterns (v0.0.8)
# ---------------------------------------------------------------------------


# Case 24: Deployer-Layout — current → releases/N/composer.json
def test_detect_typo3_deployer_layout(tmp_path: Path) -> None:
    """Composer-Mode mit deployer.org-Pattern: current → releases/N."""
    site = tmp_path / "preprod.example.com"
    release_dir = site / "releases" / "65"
    release_dir.mkdir(parents=True)

    (release_dir / "composer.json").write_text(
        '{"require": {"typo3/cms-core": "^11.5"}}',
        encoding="utf-8",
    )
    (release_dir / "composer.lock").write_text(
        '{"packages": [{"name": "typo3/cms-core", "version": "11.5.42"}]}',
        encoding="utf-8",
    )

    # current/ symlink auf releases/65/
    (site / "current").symlink_to(release_dir, target_is_directory=True)

    with patch("cci.system.inventory.apps.typo3._VAR_WWW", tmp_path):
        result = detect_typo3()

    assert len(result) == 1
    assert result[0]["name"] == "typo3"
    assert result[0]["version"] == "11.5.42"
    # path zeigt logischen Site-Root, NICHT releases/65
    assert result[0]["path"] == str(site)
    # config_file zeigt Sub-Pattern implizit
    assert result[0]["config_file"] == "current/composer.json"
    assert result[0]["mode"] == "composer"


# Case 25: typo3-base Layout — /var/www/typo3/<site>/composer.json
def test_detect_typo3_typo3_base_layout(tmp_path: Path) -> None:
    """Composer-Mode mit DevOps-Konvention /var/www/typo3/<site>/."""
    site = tmp_path / "typo3" / "example.com"
    site.mkdir(parents=True)

    (site / "composer.json").write_text(
        '{"require": {"typo3/cms-core": "^13.4"}}',
        encoding="utf-8",
    )
    (site / "composer.lock").write_text(
        '{"packages": [{"name": "typo3/cms-core", "version": "13.4.5"}]}',
        encoding="utf-8",
    )

    with patch("cci.system.inventory.apps.typo3._VAR_WWW", tmp_path):
        result = detect_typo3()

    assert len(result) == 1
    assert result[0]["version"] == "13.4.5"
    assert result[0]["path"] == str(site)
    assert result[0]["config_file"] == "composer.json"
    assert result[0]["mode"] == "composer"


# Case 26: typo3-base + Deployer kombiniert
def test_detect_typo3_typo3_base_deployer_combined(tmp_path: Path) -> None:
    """Composer-Mode mit typo3-base + Deployer: typo3/<site>/current → releases/N."""
    site = tmp_path / "typo3" / "deploy.example.com"
    release_dir = site / "releases" / "12"
    release_dir.mkdir(parents=True)

    (release_dir / "composer.json").write_text(
        '{"require": {"typo3/cms-core": "^13.4"}}',
        encoding="utf-8",
    )
    (release_dir / "composer.lock").write_text(
        '{"packages": [{"name": "typo3/cms-core", "version": "13.4.10"}]}',
        encoding="utf-8",
    )

    (site / "current").symlink_to(release_dir, target_is_directory=True)

    with patch("cci.system.inventory.apps.typo3._VAR_WWW", tmp_path):
        result = detect_typo3()

    assert len(result) == 1
    assert result[0]["version"] == "13.4.10"
    assert result[0]["path"] == str(site)
    assert result[0]["config_file"] == "current/composer.json"
    assert result[0]["mode"] == "composer"


# ---------------------------------------------------------------------------
# detect_typo3 — relative Symlinks (v0.0.9 — Live-Repro des v0.0.8-Failures)
# ---------------------------------------------------------------------------


# Case 27: Deployer-Layout mit RELATIVEM current-Symlink — Live-Failure-Repro
def test_detect_typo3_deployer_relative_symlink(tmp_path: Path) -> None:
    """Deployer-Layout mit relativem `current → releases/<N>`-Symlink.

    Live-Repro des v0.0.8-Failures auf osU2404 / preprod.scheucherparkett.com:
    Python 3.10 `pathlib.Path.glob("*/current/composer.json")` behandelte
    relative intermediate Symlinks inkonsistent — Detection lieferte
    leeres `apps:[]` trotz installierter TYPO3-Site. Bestehende Cases
    24/26 nutzten `symlink_to(target, target_is_directory=True)` mit
    absoluten Pfaden und fingen die Live-Bedingung nicht.

    v0.0.9-Fix: explizite Pfad-Auswertung via `iterdir()` + `is_file()`.
    `is_file()` folgt sowohl relativen als auch absoluten Symlinks
    deterministisch.
    """
    site = tmp_path / "preprod.example.com"
    release_dir = site / "releases" / "65"
    release_dir.mkdir(parents=True)

    (release_dir / "composer.json").write_text(
        '{"require": {"typo3/cms-core": "^11.5"}}',
        encoding="utf-8",
    )
    (release_dir / "composer.lock").write_text(
        '{"packages": [{"name": "typo3/cms-core", "version": "11.5.42-dev"}]}',
        encoding="utf-8",
    )

    # RELATIVER Symlink (deployer.org-Standard erzeugt genau dieses Pattern).
    # Kein `target_is_directory`-Hint, kein absoluter Pfad.
    (site / "current").symlink_to(Path("releases") / "65")

    with patch("cci.system.inventory.apps.typo3._VAR_WWW", tmp_path):
        result = detect_typo3()

    assert len(result) == 1
    assert result[0]["name"] == "typo3"
    assert result[0]["version"] == "11.5.42-dev"
    assert result[0]["path"] == str(site)
    assert result[0]["config_file"] == "current/composer.json"
    assert result[0]["mode"] == "composer"


# Case 28: Dangling current-Symlink — kein Crash, kein False-Positive
def test_detect_typo3_dangling_current_symlink(tmp_path: Path) -> None:
    """Dangling Symlink (Ziel existiert nicht) — defensive, kein Crash."""
    site = tmp_path / "broken.example.com"
    site.mkdir()
    # Symlink auf nicht-existentes releases/99 — current/composer.json
    # ist nicht erreichbar, is_file() returnt False.
    (site / "current").symlink_to(Path("releases") / "99")

    with patch("cci.system.inventory.apps.typo3._VAR_WWW", tmp_path):
        result = detect_typo3()

    assert result == []


# Case 29: typo3-base + Deployer mit RELATIVEM Symlink kombiniert
def test_detect_typo3_typo3_base_relative_deployer(tmp_path: Path) -> None:
    """typo3-base-Konvention + Deployer mit relativem Symlink.

    DevOps-WordOps-Konvention `/var/www/typo3/<site>/` kombiniert mit
    Deployer-Pattern `current → releases/<N>` als relativer Symlink.
    """
    site = tmp_path / "typo3" / "deploy.example.com"
    release_dir = site / "releases" / "12"
    release_dir.mkdir(parents=True)

    (release_dir / "composer.json").write_text(
        '{"require": {"typo3/cms-core": "^13.4"}}',
        encoding="utf-8",
    )
    (release_dir / "composer.lock").write_text(
        '{"packages": [{"name": "typo3/cms-core", "version": "13.4.10"}]}',
        encoding="utf-8",
    )

    # RELATIVER Symlink — wie Case 27, in typo3-base-Konvention.
    (site / "current").symlink_to(Path("releases") / "12")

    with patch("cci.system.inventory.apps.typo3._VAR_WWW", tmp_path):
        result = detect_typo3()

    assert len(result) == 1
    assert result[0]["version"] == "13.4.10"
    assert result[0]["path"] == str(site)
    assert result[0]["config_file"] == "current/composer.json"
    assert result[0]["mode"] == "composer"


# ---------------------------------------------------------------------------
# v0.0.10 — _is_typo3_composer_project OR-Logic (Custom-Wrapper-Pattern)
# ---------------------------------------------------------------------------


# Case 5b: composer.json mit typo3/cms-backend in require (kein cms-core)
def test_is_typo3_composer_project_backend_only(tmp_path: Path) -> None:
    """OR-Logic v0.0.10: irgendein typo3/cms-* in require → True.

    Custom-Wrapper-Projects bündeln oft nur einzelne typo3/cms-*-Packages
    in require (z.B. typo3/cms-backend, -frontend, -extbase), und ziehen
    typo3/cms-core transitive via composer.lock. Alte v0.0.9-Detection
    (`typo3/cms-core in require` strikt) verfehlt das — v0.0.10 OR-Logic
    erkennt es.
    """
    composer_json = tmp_path / "composer.json"
    composer_json.write_text(
        '{"require": {"typo3/cms-backend": "^12.4", "typo3/cms-frontend": "^12.4"}}',
        encoding="utf-8",
    )
    assert _is_typo3_composer_project(composer_json) is True


# ---------------------------------------------------------------------------
# v0.0.10 — _detect_typo3_project Multi-Source-Hierarchie (Pure Function)
# ---------------------------------------------------------------------------


# Case 30: Custom-Distribution Wurzel-Asche v0.0.9 — composer.json hat KEIN
# typo3/cms-core direkt, composer.lock hat es als transitive Dep
def test_detect_typo3_project_custom_distribution_lock(tmp_path: Path) -> None:
    """Live-Repro: mmcagentur-Style Custom-Distribution.

    composer.json `require` enthält nur Custom-Wrapper-Packages
    (mmcagentur/...), `typo3/cms-core` ist transitive in composer.lock.
    v0.0.9-Detection verfehlte das (Sites:(none) auf osU2404 trotz
    TYPO3 v12.4.45 installiert) — v0.0.10 Source 2 erkennt es.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "composer.json").write_text(
        '{"name": "mmcagentur/typo3-website-scheucher-parkett",'
        ' "type": "project",'
        ' "require": {"mmcagentur/typo3-base": "^1.0", "php": "^8.3"}}',
        encoding="utf-8",
    )
    (project_root / "composer.lock").write_text(
        '{"packages": ['
        '{"name": "mmcagentur/typo3-base", "version": "1.0.0"},'
        '{"name": "typo3/cms-core", "version": "v12.4.45"},'
        '{"name": "typo3/cms-backend", "version": "v12.4.45"}'
        ']}',
        encoding="utf-8",
    )

    result = _detect_typo3_project(project_root)

    assert result is not None
    assert result["version"] == "12.4.45"
    assert result["source"] == "composer-lock"
    assert result["mode"] == "composer"


# Case 31: vendor-only Detection (kein composer.lock, kein composer.json)
def test_detect_typo3_project_vendor_only(tmp_path: Path) -> None:
    """Source 1 vendor-php als alleinige Quelle.

    Edge-Case: installed TYPO3 ohne erreichbare composer-Meta-Dateien
    (z.B. nach manuellem Cleanup). Detection bleibt funktional via
    vendor/typo3/cms-core/Classes/Information/Typo3Version.php.
    """
    project_root = tmp_path / "project"
    vendor_dir = project_root / "vendor" / "typo3" / "cms-core" / "Classes" / "Information"
    vendor_dir.mkdir(parents=True)
    (vendor_dir / "Typo3Version.php").write_text(
        "<?php\nclass Typo3Version {\n"
        "    protected const VERSION = '13.4.1';\n}\n",
        encoding="utf-8",
    )

    result = _detect_typo3_project(project_root)

    assert result is not None
    assert result["version"] == "13.4.1"
    assert result["source"] == "vendor-php"
    assert result["mode"] == "composer"


# Case 31b: vendor existiert aber Typo3Version.php hat KEIN parsbares VERSION
# → Fallback zu composer.lock für echte Version (Partial-Install-Edge-Case)
def test_detect_typo3_project_vendor_partial_lock_fallback(tmp_path: Path) -> None:
    """Partial-Install: vendor-Dir da, aber Typo3Version.php fehlt VERSION-Konst.

    Senior-Hint (AI045): edge-case wo vendor existiert aber Version-Parse
    _UNKNOWN ergibt. v0.0.10 fallback zu composer.lock für echte Version,
    aber source bleibt vendor-php (TYPO3 ist installiert, nur Version-Parse
    failed).
    """
    project_root = tmp_path / "project"
    vendor_dir = project_root / "vendor" / "typo3" / "cms-core" / "Classes" / "Information"
    vendor_dir.mkdir(parents=True)
    # Typo3Version.php existiert aber ohne VERSION-Konstante (Partial-File)
    (vendor_dir / "Typo3Version.php").write_text(
        "<?php\nclass Typo3Version { /* incomplete */ }\n",
        encoding="utf-8",
    )
    (project_root / "composer.lock").write_text(
        '{"packages": [{"name": "typo3/cms-core", "version": "12.4.45"}]}',
        encoding="utf-8",
    )

    result = _detect_typo3_project(project_root)

    assert result is not None
    assert result["version"] == "12.4.45"  # via lock-Fallback
    assert result["source"] == "vendor-php"  # vendor existiert → primary
    assert result["mode"] == "composer"


# Case 32: composer.json mit typo3/cms-* in require, kein vendor, kein lock
def test_detect_typo3_project_composer_json_only(tmp_path: Path) -> None:
    """Source 3 composer-json: nur Constraint verfügbar, keine resolved Version.

    Pre-Install-Edge-Case: composer.json sagt TYPO3 (via cms-backend),
    aber composer install ist nicht gelaufen. version=_UNKNOWN als
    Detection-Result.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "composer.json").write_text(
        '{"type": "project", "require": {"typo3/cms-backend": "^13.4"}}',
        encoding="utf-8",
    )

    result = _detect_typo3_project(project_root)

    assert result is not None
    assert result["version"] == "unknown"
    assert result["source"] == "composer-json"
    assert result["mode"] == "composer"


# Case 33: Multi-Source-Konsistenz — alle drei Sources verfügbar
# → Priorität vendor-php (Source 1)
def test_detect_typo3_project_multi_source_priority(tmp_path: Path) -> None:
    """Detection-Hierarchie: erste positive Source (vendor-php) gewinnt.

    Alle drei Sources liefern konsistente Version. Pure-Function returnt
    Source 1 (vendor-php, autoritativ-lokal). Version-Konsistenz-Check
    selbst kommt in v0.0.11 mit Composer-CLI (Case 33b Schema-Drift-Warning).
    """
    project_root = tmp_path / "project"
    vendor_dir = project_root / "vendor" / "typo3" / "cms-core" / "Classes" / "Information"
    vendor_dir.mkdir(parents=True)
    (vendor_dir / "Typo3Version.php").write_text(
        "<?php\nclass Typo3Version {\n"
        "    protected const VERSION = '12.4.45';\n}\n",
        encoding="utf-8",
    )
    (project_root / "composer.lock").write_text(
        '{"packages": [{"name": "typo3/cms-core", "version": "12.4.45"}]}',
        encoding="utf-8",
    )
    (project_root / "composer.json").write_text(
        '{"require": {"typo3/cms-core": "^12.4"}}',
        encoding="utf-8",
    )

    result = _detect_typo3_project(project_root)

    assert result is not None
    assert result["version"] == "12.4.45"
    assert result["source"] == "vendor-php"  # Priorität (Source 1)
    assert result["mode"] == "composer"


# Case 34: Non-TYPO3 Project (laravel) → None
def test_detect_typo3_project_non_typo3(tmp_path: Path) -> None:
    """Defense: non-TYPO3 Composer-Project (Laravel) wird NICHT als TYPO3 erkannt."""
    project_root = tmp_path / "laravel-site"
    project_root.mkdir()
    (project_root / "composer.json").write_text(
        '{"require": {"laravel/framework": "^11.0", "php": "^8.2"}}',
        encoding="utf-8",
    )
    (project_root / "composer.lock").write_text(
        '{"packages": [{"name": "laravel/framework", "version": "11.0.0"}]}',
        encoding="utf-8",
    )

    result = _detect_typo3_project(project_root)

    assert result is None


# Case 35: Leeres / non-existing project_root → None
def test_detect_typo3_project_empty_root(tmp_path: Path) -> None:
    """Defense: project_root ohne irgendwelche Composer-Files → None."""
    project_root = tmp_path / "empty-project"
    project_root.mkdir()

    result = _detect_typo3_project(project_root)

    assert result is None

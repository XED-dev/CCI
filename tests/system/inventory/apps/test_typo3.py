"""Tests für cci.system.inventory.apps.typo3 — TYPO3-Detector + Registry."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cci.system.inventory.apps import (
    DETECTORS,
    collect_apps_info,
)
from cci.system.inventory.apps.typo3 import (
    _parse_typo3_version,
    detect_typo3,
)


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


# Case 5: detect_typo3 mit fingiertem htdocs-Layout
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


# Case 5b: detect_typo3 mit flat-Layout (typo3conf direkt unter Site-Root,
# kein htdocs/-Subordner) — schließt Coverage-Lücke aus SS4-Sweep O1.
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


# Case 6: detect_typo3 mit nicht-existentem /var/www/ -> leere Liste
def test_detect_typo3_no_var_www(tmp_path: Path) -> None:
    fake_path = tmp_path / "nonexistent"
    with patch("cci.system.inventory.apps.typo3._VAR_WWW", fake_path):
        result = detect_typo3()
    assert result == []


# Case 7: detect_typo3 mit existing /var/www/ aber keinem typo3 -> leere Liste
def test_detect_typo3_no_typo3_installations(tmp_path: Path) -> None:
    """Statisches Site ohne typo3conf/LocalConfiguration.php -> 0 Treffer."""
    static_site = tmp_path / "static-site"
    static_site.mkdir()
    (static_site / "index.html").write_text("hello", encoding="utf-8")

    with patch("cci.system.inventory.apps.typo3._VAR_WWW", tmp_path):
        result = detect_typo3()
    assert result == []


# Case 8: collect_apps_info nutzt DETECTORS-Registry
def test_collect_apps_info_uses_registry(tmp_path: Path) -> None:
    """collect_apps_info iteriert DETECTORS — leere Box -> leere Liste."""
    fake_path = tmp_path / "nonexistent"
    with patch("cci.system.inventory.apps.typo3._VAR_WWW", fake_path):
        result = collect_apps_info()
    assert isinstance(result, list)
    assert result == []


# Case 9: DETECTORS-Registry enthält erwartete Detector-Funktionen
def test_detectors_registry_contains_typo3() -> None:
    """v0.0.1: nur typo3 in Registry. Lakmus-Test gegen versehentliche
    Pre-Optimization (pluggy/zusätzliche Detectors)."""
    assert "typo3" in DETECTORS
    assert callable(DETECTORS["typo3"])
    # Phase 1 v0.0.1: nur ein Detector — weitere Apps als v0.x-Backlog
    assert len(DETECTORS) == 1

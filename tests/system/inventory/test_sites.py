"""Tests für cci.system.inventory.sites — Werkzeug-First-Site-Enumeration (v0.0.10)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from cci.system.inventory.sites import (
    _list_wordops_sites,
    _parse_nginx_site_config,
    _resolve_project_root,
    collect_sites_info,
)


# ---------------------------------------------------------------------------
# _list_wordops_sites (Subprocess-Layer, mocked safe_run)
# ---------------------------------------------------------------------------


def test_list_wordops_sites_returns_domains() -> None:
    """`wo site list` stdout → Liste Domain-Namen, getrimmt."""
    mock_result = MagicMock(
        returncode=0,
        stdout="domain1.com\ndomain2.com\n  domain3.com  \n",
    )
    with patch("cci.system.inventory.sites.safe_run", return_value=mock_result):
        result = _list_wordops_sites()
    assert result == ["domain1.com", "domain2.com", "domain3.com"]


def test_list_wordops_sites_empty_on_file_not_found() -> None:
    """Bei FileNotFoundError (wo nicht installiert) → leere Liste."""
    with patch(
        "cci.system.inventory.sites.safe_run", side_effect=FileNotFoundError
    ):
        result = _list_wordops_sites()
    assert result == []


def test_list_wordops_sites_empty_on_nonzero_exit() -> None:
    """Bei non-zero exit code → leere Liste."""
    mock_result = MagicMock(returncode=1, stdout="")
    with patch("cci.system.inventory.sites.safe_run", return_value=mock_result):
        result = _list_wordops_sites()
    assert result == []


# ---------------------------------------------------------------------------
# _parse_nginx_site_config (Pure-Parse mit tmp_path-Fixtures)
# ---------------------------------------------------------------------------


def test_parse_nginx_config_extracts_root_and_php(tmp_path: Path) -> None:
    """Standard-WordOps-Config → (webroot, php_version)."""
    config = tmp_path / "site.conf"
    config.write_text(
        "server {\n"
        "    root /var/www/example.com/public;\n"
        "    include common/php83.conf;\n"
        "}\n",
        encoding="utf-8",
    )
    webroot, php = _parse_nginx_site_config(config)
    assert webroot == "/var/www/example.com/public"
    assert php == "8.3"


def test_parse_nginx_config_ignores_comment_lines(tmp_path: Path) -> None:
    """Auskommentierte Direktiven (^# ...) werden ignoriert.

    Live-Realität auf osU2404: DevOps macht manuelle Notizen via
    `#   root /var/www/<site>/htdocs;` als Kommentar — meine
    Detection darf nur aktive (uncommented) Direktiven nehmen.
    """
    config = tmp_path / "site.conf"
    config.write_text(
        "server {\n"
        "#   root /var/www/example.com/htdocs;\n"
        "    root /var/www/example.com/public;\n"
        "#   include common/php74.conf;\n"
        "    include common/php83.conf;\n"
        "#   include common/php84.conf;\n"
        "}\n",
        encoding="utf-8",
    )
    webroot, php = _parse_nginx_site_config(config)
    assert webroot == "/var/www/example.com/public"
    assert php == "8.3"


def test_parse_nginx_config_missing_file() -> None:
    """Non-existent File → (None, None) defensive."""
    webroot, php = _parse_nginx_site_config(Path("/nonexistent/file.conf"))
    assert webroot is None
    assert php is None


def test_parse_nginx_config_no_root_directive(tmp_path: Path) -> None:
    """Config ohne `root` → webroot=None (z.B. redirect-only server-block)."""
    config = tmp_path / "site.conf"
    config.write_text(
        "server {\n"
        "    server_name www.example.com;\n"
        "    return 301 $scheme://example.com$request_uri;\n"
        "}\n",
        encoding="utf-8",
    )
    webroot, _ = _parse_nginx_site_config(config)
    assert webroot is None


def test_parse_nginx_config_php_version_formats(tmp_path: Path) -> None:
    """PHP-Version-Format: php74→7.4, php83→8.3, php100→10.0 (defensive)."""
    for digits, expected in [("74", "7.4"), ("80", "8.0"), ("83", "8.3"), ("100", "10.0")]:
        config = tmp_path / f"site-{digits}.conf"
        config.write_text(
            "server {\n"
            "    root /var/www/x.com/htdocs;\n"
            f"    include common/php{digits}.conf;\n"
            "}\n",
            encoding="utf-8",
        )
        _, php = _parse_nginx_site_config(config)
        assert php == expected, f"php{digits} → expected {expected}, got {php!r}"


# ---------------------------------------------------------------------------
# _resolve_project_root (Pure-Function)
# ---------------------------------------------------------------------------


def test_resolve_project_root_composer_public_layout() -> None:
    """Composer-Layout: Webroot `*/public/` → Parent als Project-Root."""
    result = _resolve_project_root("/var/www/example.com/public")
    assert result == Path("/var/www/example.com")


def test_resolve_project_root_classic_htdocs_layout() -> None:
    """Classic-Mode / htdocs-Layout: Webroot IST Project-Root."""
    result = _resolve_project_root("/var/www/example.com/htdocs")
    assert result == Path("/var/www/example.com/htdocs")


def test_resolve_project_root_deployer_layout() -> None:
    """Deployer + public: Project-Root ist current/, NICHT releases/N/.

    Live-Pattern auf osU2404: /var/www/<site>/current/public (current
    ist Symlink auf releases/65). Webroot vom Nginx-root-Direktive
    deutet auf .../current/public — Project-Root ist .../current
    (Composer-Files liegen direkt unter current/).
    """
    result = _resolve_project_root("/var/www/preprod.scheucherparkett.com/current/public")
    assert result == Path("/var/www/preprod.scheucherparkett.com/current")


# ---------------------------------------------------------------------------
# collect_sites_info (Integration mit mocked subprocess + tmp_path-Fixtures)
# ---------------------------------------------------------------------------


def test_collect_sites_info_single_typo3_site(tmp_path: Path) -> None:
    """Integration: 1 Domain → 1 SiteEntry mit cms=typo3 + 1 DomainInfo."""
    nginx_dir = tmp_path / "nginx" / "sites-available"
    nginx_dir.mkdir(parents=True)

    project_root = tmp_path / "var" / "www" / "example.com"
    vendor_dir = (
        project_root / "vendor" / "typo3" / "cms-core" / "Classes" / "Information"
    )
    vendor_dir.mkdir(parents=True)
    (vendor_dir / "Typo3Version.php").write_text(
        "<?php\nclass Typo3Version { protected const VERSION = '13.4.1'; }",
        encoding="utf-8",
    )
    public_dir = project_root / "public"
    public_dir.mkdir()

    (nginx_dir / "example.com").write_text(
        "server {\n"
        f"    root {public_dir};\n"
        "    include common/php83.conf;\n"
        "}\n",
        encoding="utf-8",
    )

    mock_result = MagicMock(returncode=0, stdout="example.com\n")

    with patch(
        "cci.system.inventory.sites.safe_run", return_value=mock_result
    ), patch("cci.system.inventory.sites._NGINX_SITES_DIR", nginx_dir):
        result = collect_sites_info()

    assert len(result) == 1
    site = result[0]
    assert site["cms"] == "typo3"
    assert site["cms_version"] == "13.4.1"
    assert site["cms_source"] == "vendor-php"
    assert site["webroot"] == str(public_dir)
    assert site["project_root"] == str(project_root)
    assert len(site["domains"]) == 1
    assert site["domains"][0]["domain"] == "example.com"
    assert site["domains"][0]["php_version"] == "8.3"


def test_collect_sites_info_multi_webroot_mapping(tmp_path: Path) -> None:
    """Live-Repro: 3 Domains teilen 1 Webroot mit unterschiedlichen PHP-Versions.

    Realität auf osU2404 2026-05-17:
    - preprod.scheucherparkett.com (PHP 7.4)
    - scheucherparkett.at (PHP 8.3)
    - web.scheucherparkett.at (PHP 7.4)
    Alle drei: root /var/www/preprod.scheucherparkett.com/public

    Erwartung: 1 SiteEntry (Webroot-Gruppierung per DevOps-Vote b),
    3 DomainInfo als Attribute.
    """
    nginx_dir = tmp_path / "nginx" / "sites-available"
    nginx_dir.mkdir(parents=True)

    project_root = tmp_path / "var" / "www" / "preprod.scheucherparkett.com"
    public_dir = project_root / "public"
    public_dir.mkdir(parents=True)
    (project_root / "composer.lock").write_text(
        '{"packages": [{"name": "typo3/cms-core", "version": "12.4.45"}]}',
        encoding="utf-8",
    )

    for domain, php in [
        ("preprod.scheucherparkett.com", "74"),
        ("scheucherparkett.at", "83"),
        ("web.scheucherparkett.at", "74"),
    ]:
        (nginx_dir / domain).write_text(
            "server {\n"
            f"    root {public_dir};\n"
            f"    include common/php{php}.conf;\n"
            "}\n",
            encoding="utf-8",
        )

    mock_result = MagicMock(
        returncode=0,
        stdout=(
            "preprod.scheucherparkett.com\n"
            "scheucherparkett.at\n"
            "web.scheucherparkett.at\n"
        ),
    )

    with patch(
        "cci.system.inventory.sites.safe_run", return_value=mock_result
    ), patch("cci.system.inventory.sites._NGINX_SITES_DIR", nginx_dir):
        result = collect_sites_info()

    assert len(result) == 1, "Shared Webroot → 1 SiteEntry"
    site = result[0]
    assert site["cms"] == "typo3"
    assert site["cms_version"] == "12.4.45"
    assert site["cms_source"] == "composer-lock"
    assert len(site["domains"]) == 3
    domain_names = {d["domain"] for d in site["domains"]}
    assert domain_names == {
        "preprod.scheucherparkett.com",
        "scheucherparkett.at",
        "web.scheucherparkett.at",
    }
    php_by_domain = {d["domain"]: d["php_version"] for d in site["domains"]}
    assert php_by_domain["preprod.scheucherparkett.com"] == "7.4"
    assert php_by_domain["scheucherparkett.at"] == "8.3"
    assert php_by_domain["web.scheucherparkett.at"] == "7.4"


def test_collect_sites_info_empty_when_wo_unavailable() -> None:
    """Wenn `wo site list` non-zero exit → leere Liste, kein Crash."""
    mock_result = MagicMock(returncode=1, stdout="")
    with patch(
        "cci.system.inventory.sites.safe_run", return_value=mock_result
    ):
        result = collect_sites_info()
    assert result == []


def test_collect_sites_info_unknown_cms_lists_site(tmp_path: Path) -> None:
    """Non-TYPO3-Webroot (htdocs-Pattern ohne TYPO3-Files) → cms="unknown".

    Die Site wird trotzdem gelistet (SysOps sieht alle Sites pro Webroot),
    nur ohne TYPO3-spezifische Felder (cms_version="unknown", source="").
    """
    nginx_dir = tmp_path / "nginx" / "sites-available"
    nginx_dir.mkdir(parents=True)
    htdocs_dir = tmp_path / "var" / "www" / "wp-site.com" / "htdocs"
    htdocs_dir.mkdir(parents=True)

    (nginx_dir / "wp-site.com").write_text(
        "server {\n"
        f"    root {htdocs_dir};\n"
        "    include common/php82.conf;\n"
        "}\n",
        encoding="utf-8",
    )

    mock_result = MagicMock(returncode=0, stdout="wp-site.com\n")

    with patch(
        "cci.system.inventory.sites.safe_run", return_value=mock_result
    ), patch("cci.system.inventory.sites._NGINX_SITES_DIR", nginx_dir):
        result = collect_sites_info()

    assert len(result) == 1
    site = result[0]
    assert site["cms"] == "unknown"
    assert site["cms_version"] == "unknown"
    assert site["cms_source"] == ""
    assert site["config_file"] == ""
    assert site["domains"][0]["domain"] == "wp-site.com"
    assert site["domains"][0]["php_version"] == "8.2"


def test_collect_sites_info_skips_domain_without_root_directive(tmp_path: Path) -> None:
    """Domain mit Nginx-Config ohne `root` (redirect-only) wird übersprungen."""
    nginx_dir = tmp_path / "nginx" / "sites-available"
    nginx_dir.mkdir(parents=True)

    (nginx_dir / "redirect.com").write_text(
        "server {\n"
        "    server_name redirect.com;\n"
        "    return 301 $scheme://canonical.com$request_uri;\n"
        "}\n",
        encoding="utf-8",
    )

    mock_result = MagicMock(returncode=0, stdout="redirect.com\n")

    with patch(
        "cci.system.inventory.sites.safe_run", return_value=mock_result
    ), patch("cci.system.inventory.sites._NGINX_SITES_DIR", nginx_dir):
        result = collect_sites_info()

    # Domain ohne root → skip → leere Liste
    assert result == []

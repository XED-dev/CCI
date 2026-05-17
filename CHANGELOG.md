# Changelog

Alle bemerkenswerten Änderungen an `xed-cci` werden hier dokumentiert.

Format folgt [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/).

## [0.0.10] — 2026-05-17

### ⚠ BREAKING — Werkzeug-First-Architektur + Webroot-zentriertes Site-Schema

v0.0.10 fixt die Wurzel der v0.0.9-Live-Asche (Sites:(none) auf osU2404
trotz 9 echter WordOps-Sites mit TYPO3 v12.4.45 installiert) und legt
die Architektur strukturell neu:

1. **Detection-Multi-Source-Hierarchie** (Sub-Sprint J):
   alte `_is_typo3_composer_project`-Detection prüfte nur direkter
   `typo3/cms-core` in `require` — verfehlte Custom-Distribution-Wrapper
   (z.B. `mmcagentur/typo3-website-...`) die `typo3/cms-core` nur
   transitive via composer.lock haben. v0.0.10 erweitert auf
   Multi-Source-Hierarchie: vendor-FS → composer.lock → composer.json
   (mit OR-Logic auf `typo3/cms-*`).

2. **Werkzeug-First-Site-Enumeration** (Sub-Sprint K, neuer File
   `sites.py`): `wo site list` als Primärquelle + Nginx-Config-Parse
   für Webroot+PHP-Version (autoritativ). Ersetzt legacy
   `/var/www/`-iterdir-Heuristik. Multi-Webroot-Mapping erfasst Sites
   die denselben Webroot teilen mit unterschiedlichen PHP-Versionen.

3. **Box-Klassen-Pre-Step** (Sub-Sprint N, neuer File `box_class.py`):
   Hard-Gate vor Inventur — Ubuntu LTS 22.04/24.04 + `wo` im PATH +
   `nginx-wo`-Paket installiert. Bei Mismatch Exit 2 mit Diagnostik.

**Konsumenten-Migration:**

| Alt (v0.0.9) | Neu (v0.0.10) |
|---|---|
| `report["sites"]` = `list[AppInfo]` (pro Site) | `list[SiteEntry]` (pro Webroot mit nested DomainInfo) |
| `AppInfo` mit `name`, `version`, `path`, `config_file`, `mode` | `SiteEntry` mit `webroot`, `project_root`, `cms`, `cms_version`, `cms_mode`, `cms_source`, `config_file`, `domains` |
| Eine TYPO3-Site = ein AppInfo (auch wenn Webroot shared) | Ein Webroot = ein SiteEntry (auch wenn 3 Domains drauf zeigen) |
| Output: 1 Site pro Domain | Output: 1 Site pro Webroot + Domain-Liste pro Site |

**JSON-Schema-Bump 0.0.2 → 0.0.3:** Sub-Struktur von `sites[]` ist
BREAKING. AI-Agent-Konsumenten + Skripte müssen auf neue SiteEntry-
Felder umgestellt werden.

### Behoben (Sub-Sprint J — apps:[]-Wurzel-Fix endgültig)

- **`apps/typo3.py`: `_detect_typo3_project(project_root)` als neue
  Pure-Function** mit Multi-Source-Detection-Hierarchie:
  1. vendor-php (autoritativ, installed)
  2. composer-lock (transitive)
  3. composer-json (Constraint, mit OR-Logic auf `typo3/cms-*`)
- **`_is_typo3_composer_project` erweitert auf OR-Logic:**
  `typo3/cms-core` ODER irgendein `typo3/cms-*`-Package matchend.
  Live-Realität auf osU2404 bestätigt: Custom-Wrapper-Sites haben
  `typo3/cms-core` nur transitive in composer.lock.
- **Plus Partial-Install-Edge-Case:** vendor existiert aber
  Typo3Version.php hat keine VERSION-Konstante → Fallback zu lock
  für echte Version. Source bleibt vendor-php (TYPO3 ist installiert).

### Hinzugefügt (Sub-Sprint K — Werkzeug-First-Site-Enumeration)

- **Neuer File `cci/system/inventory/sites.py`** mit:
  - `_list_wordops_sites()` via `wo site list` (safe_run-whitelisted)
  - `_parse_nginx_site_config()` pure-Parse: `root` + `include common/phpXY.conf`
  - `_resolve_project_root()`: Parent von `*/public` (Composer-Layout)
  - `collect_sites_info()` mit Webroot-Gruppierung (DevOps-Vote
    2026-05-17: „Webroot ist Quelle der Wahrheit, Domain ist View darauf")
- **safe_run COMMAND_WHITELIST erweitert:** `wo` mit
  `frozenset({"site", "info", "--help", "-h"})`. CAVEAT-Kommentar
  dokumentiert dass mutierende `wo site create`/`delete`-Aufrufe
  durch cmd[1]='site' theoretisch durchsetzbar sind — werden aber
  nur von cci-Code aufgerufen (kein User-Input).
- **Plus erste Erkenntnis aus Live-Realität:** `wo site info` ist NICHT
  autoritativ für aktuelle PHP-Version (zeigt WordOps-Internal-Config,
  driftet bei manueller Nginx-Edit). Nginx-Config-Parse autoritativ.

### Hinzugefügt (Sub-Sprint N — Box-Klassen-Pre-Step)

- **Neuer File `cci/system/inventory/box_class.py`** mit
  `verify_typo3_box_class()` und Helpers `_check_ubuntu_lts()`,
  `_check_wo_binary()`, `_check_nginx_wo_installed()`. Returns
  `BoxClassCheckResult(ok, errors, diagnostics)`.
- **`inventory_command` Pre-Step:** vor Composition wird
  `verify_typo3_box_class()` aufgerufen. Bei ok=False: Mismatch-
  Banner + Errors + Diagnostik nach stderr, Exit 2.
- **Stack-Komponenten** (Multi-PHP, MariaDB, Solr, Composer-CLI)
  bleiben bewusst out-of-scope für Pre-Step — saubere Schicht-
  Trennung Box-Identifikation vs Stack-Inventur (v0.0.12+).

### Geändert (Output-Datenmodell + Rich-Rendering)

- **`SiteEntry` + `DomainInfo` TypedDicts** in `sites.py`:
  - `SiteEntry`: webroot, project_root, cms, cms_version, cms_mode,
    cms_source, config_file, domains
  - `DomainInfo`: domain, php_version, nginx_config
- **`_render_sites` mit Tree-Output** für nested Multi-Domain pro
  Webroot (├─/└─ UTF-8-Box-Drawing).
- **`_render_oneliner` + `_render_text`** analog mit Webroot-Gruppen.

### Tests

- 8 neue Cases in `test_typo3.py`:
  - Case 5b: OR-Logic mit `typo3/cms-backend` (Custom-Wrapper)
  - Case 30: Custom-Distribution mit composer.lock-transitive
  - Case 31: vendor-only Detection
  - Case 31b: vendor + Typo3Version.php-partial → Fallback lock
  - Case 32: composer.json mit `typo3/cms-*` (kein vendor/lock)
  - Case 33: Multi-Source-Konsistenz, vendor-Priorität
  - Case 34: non-TYPO3 (Laravel) → None
  - Case 35: leerer project_root → None
- 16 neue Cases in `test_sites.py` (Werkzeug-First-Enumeration):
  - `_list_wordops_sites` mit mocked subprocess
  - `_parse_nginx_site_config` mit Kommentar-Stripping, PHP-Versions-Mapping
  - `_resolve_project_root` für public/htdocs/deployer-Layouts
  - `collect_sites_info` Integration inkl. Multi-Webroot-Mapping
    (Live-Repro: 3 Domains teilen 1 Webroot mit 7.4/8.3/7.4)
- 17 neue Cases in `test_box_class.py` (Pre-Step):
  - `_parse_os_release` mit Quotes/Comments
  - `_check_ubuntu_lts` mit Match (22.04/24.04) + Mismatch (Debian/20.04/missing)
  - `_check_wo_binary` mit shutil.which-Mock
  - `_check_nginx_wo_installed` mit dpkg-query-Mock
  - `verify_typo3_box_class` Integration (Match + Mismatch-Cases)
- 1 neuer Case in `test_inventory.py`:
  - `test_inventory_command_exits_on_box_mismatch` (Pre-Step Hard-Gate)
- Plus `tests/conftest.py` mit autouse-Mock für CLI-Invocation-Tests.
- 130/130 pytest grün auf der Workstation (vormals 88/88 in v0.0.9).

### Pattern-Anker

Architektur-Wurzel-Lehre (drei Aschen-Pattern dieser Session):
„rate-herumprogrammieren statt Doku/Realität-First" ist Anti-Pattern.
Doku + Community + Live-Realität sind autoritative Quellen — Pattern-
Recall ohne Verifikation ist Asche-Wurzel. v0.0.10 bricht das Pattern
durch WebFetch-Doku-Recherche (Composer-Schema + TYPO3-BaseDistribution
+ WordOps-Doku) plus systematische Live-Daten-Sammlung auf osU2404.

cci muss SELBSTSTÄNDIG alle Eventualitäten erkennen (DevOps-Direktive
2026-05-17): robuste Multi-Source-Detection statt strikte Single-Source.
Pattern-Anker: Detection-Hierarchie mit klarer Priorität (autoritativ
zuerst, Fallback zuletzt) + neutrale source-Field für Diagnose.

Webroot-zentriertes Site-Schema (DevOps-Vote 2026-05-17): „Webroot ist
Quelle der Wahrheit, Domain ist View darauf." Multi-Webroot-Mapping
ist Realität (3 Sites teilen Code-Webroot mit unterschiedlichen PHP-
Versionen), nicht Anomalie — nested SiteEntry+DomainInfo macht das
natürlich konsumierbar.

[0.0.10]: https://github.com/XED-dev/CCI/releases/tag/v0.0.10

## [0.0.9] — 2026-05-15

### ⚠ BREAKING — Architektur-Neufundierung auf Box-Klassen

cci adressiert ab v0.0.9 eine eingegrenzte Box-Klasse über verb-basierte
Subkommandos. Das vormals generische `cci inventory`-Verb ist hart
entfernt (keine Deprecation-Alias-Phase — v0.0.x-SemVer „Kindergarten"
signalisiert Architektur-Instabilität, klare Migration in einem Schritt).

**Konsumenten-Migration:**

| Alt (v0.0.8) | Neu (v0.0.9) |
|---|---|
| `cci inventory` | `cci typo3` |
| `cci inventory --section apps` | `cci typo3 --section sites` |
| `cci inventory --section os` (sonstige Sections unverändert) | `cci typo3 --section os` |
| `cci inventory --format json` | `cci typo3 --format json` |
| `report["apps"]` im JSON | `report["sites"]` im JSON |

**JSON-Schema-Bump 0.0.1 → 0.0.2:** Top-Level-Key `apps` → `sites`.
AI-Agent-Konsumenten und Skripte mit `report["apps"]` müssen auf
`report["sites"]` umgestellt werden. Detector-Layer-Code (`AppInfo` +
`collect_apps_info()` + `system/inventory/apps/`) bleibt namentlich
unverändert — Section-Naming folgt Output-Domain (TYPO3-Site),
Detector-Naming folgt Implementation-Domain (Server-Apps).

### Behoben (Sub-Sprint A — `apps:[]`-Wurzel-Fix v0.0.8 Live-Failure)

- **`apps/typo3.py`: `pathlib.glob()` → explizite Pfad-Auswertung via
  `iterdir()` + `is_file()`.**
  v0.0.8 nutzte `_VAR_WWW.glob("*/current/composer.json")` für die
  Deployer-Layout-Detection. Python 3.10 `pathlib.Path.glob()` ist mit
  intermediate relativem Symlink (deployer.org-Standard
  `current → releases/<N>/`) unzuverlässig — Live-Failure auf osU2404
  zeigte `apps:(none)` trotz installierter TYPO3-Site
  (preprod.scheucherparkett.com mit Deployer-Layout). pytest 83/83
  grün, weil die Tests `symlink_to(target, target_is_directory=True)`
  mit absoluten Pfaden nutzten — die echte Live-Bedingung (relativer
  Symlink) wurde nicht reproduziert.

  **Refactor:** Vier Layout-Patterns (Top-Level + Deployer + typo3-base
  + typo3-base+Deployer) auf zwei explizite Pfad-Tests pro
  Site-Verzeichnis aufgelöst:
  - `<site>/composer.json` (Mainstream)
  - `<site>/current/composer.json` (Deployer — `is_file()` folgt
    relative + absolute Symlinks deterministisch)

  Zwei Iterations-Ebenen: direkte Sites unter `/var/www/<site>/`,
  zusätzlich `typo3/`-Konvention `/var/www/typo3/<sub-site>/`.

  Plus neue Helper `_safe_is_file()` + `_safe_is_dir()` mit
  PermissionError-Defense (Workstation-Realität: `/var/www/html/`-
  Apache-Standard für non-www-data-User nicht lesbar).

### Geändert (Sub-Sprint G — CLI-Verb-Switch + Section-Rename + Schema-Bump)

- **CLI-Verb-Switch `cci inventory` → `cci typo3`.**
  v0.0.8 hatte ein generisches `inventory`-Verb. v0.0.9 stellt um auf
  verb-basierte Box-Klassen-Subkommandos: `cci typo3` adressiert
  WordOps-LEMP-Ubuntu-LTS-Box mit TYPO3-Composer + ADD-ONs (z.B.
  Apache Solr). Künftige Box-Klassen (`cci wordpress`, …) als weitere
  Top-Level-Verben analog.

- **Section-Rename `apps` → `sites`.**
  `Section.APPS = "apps"` → `Section.SITES = "sites"`. JSON-Output-Key
  `report["apps"]` → `report["sites"]`. Render-Funktion `_render_apps()`
  → `_render_sites()` mit Tabellen-Titel "Sites" (vormals
  "Server-Apps"). Detector-Layer (`AppInfo` + `collect_apps_info` +
  `system/inventory/apps/`) bleibt unverändert — Output-Aggregation und
  Implementation sind getrennte Naming-Layers.

- **`cci -h` Top-Level-Hilfe substantiell erweitert.**
  Box-Klassen-Übersicht mit Kurzbeschreibung + Beispiel-Subkommandos +
  Output-Format-Beispiele direkt im `cci --help`-Output. Werkzeug-First:
  eine autoritative Hilfe-Quelle, die `firstboot.sh` direkt aufruft
  (Sub-Sprint H).

- **JSON-Schema 0.0.1 → 0.0.2** (BREAKING-Bump, siehe oben).

### Geändert (Sub-Sprint H — firstboot.sh Werkzeug-First)

- **`docs/firstboot.sh`: statischer Hint-Block durch `cci -h`-Aufruf
  ersetzt.**
  v0.0.7-v0.0.8 hatten den Phase-4-Hint-Block als statisches
  Bash-Echo-Konstrukt. v0.0.9 ruft `${PIPX_BIN_DIR_PATH}/cci -h` direkt
  auf — eine Pflege-Stelle statt parallel-gepflegter Hilfe.

- **firstboot.sh-VERSION-Konstante 0.0.7 → 0.0.9** (Tool-Version-Sync).

### Tests

- 3 neue Cases in `test_typo3.py` für die echte Live-Repro:
  - Case 27: Deployer-Layout mit RELATIVEM `current → releases/N`-Symlink
  - Case 28: Dangling current-Symlink — kein Crash, kein False-Positive
  - Case 29: typo3-base + Deployer mit relativem Symlink kombiniert

- 2 neue Cases in `test_cli.py`:
  - `test_help_shows_box_classes_overview` (Box-Klassen-Übersicht in `cci -h`)
  - `test_typo3_section_sites_runs` (Section-Rename `apps` → `sites`)

- Section-Filter-Tests in `test_inventory.py` durchgängig von
  `inventory`-Verb auf `typo3`-Verb und von `apps`-Key auf `sites`-Key
  umgestellt.

- 88/88 pytest grün auf der Workstation (vormals 83/83 in v0.0.8).

### Pattern-Anker

Architektur-Neufundierung auf Box-Klassen (DevOps-Direktive 2026-05-13
Abend + AI045-Senior-Sweep 2026-05-15): cci adressiert eingegrenzte
Box-Klassen, nicht generische Linux-Inventur. Pfade und Werkzeuge sind
bekannt, nicht zu detecten. Pattern-Anker: Section-Naming folgt
Output-Domain (TYPO3-Site), Detector-Naming folgt Implementation-Domain
(Server-Apps) — beide Konventionen koexistieren bewusst.

Verify-First-Disziplin (AI043-OFF §5 Q3): pytest grün ≠ Sprint-Erfolg.
Live-Acceptance auf der Ziel-Box auf allen drei Install-Pfaden (pip-dist
+ Pages-CDN + PyPI-Curl-Install) ist Pre-Condition für Tag/Release.
v0.0.8-Asche: PyPI-Tag vor Live-Verify gesetzt, `apps:[]`-Bug-Fix
wirkte nicht live. v0.0.9 setzt Tag nur nach Stage-1-grün (lokaler
whl-Install auf osU2404 mit Acceptance `cci typo3 --section sites`
zeigt typo3 + Pfad).

PermissionError-Defense für pathlib-stat-Operationen: `_safe_is_file()`
+ `_safe_is_dir()` Helper sind robust gegen Workstation-Realität
(eingeschränkte Permissions auf `/var/www/html/`-Standard-Apache-
Verzeichnis für non-www-data-User). Live-Use auf root ist nicht der
einzige Anwendungsfall — Tests müssen Workstation-Permissions auch
passieren.

[0.0.9]: https://github.com/XED-dev/CCI/releases/tag/v0.0.9

## [0.0.8] — 2026-05-13

### Behoben + Hinzugefügt (Deployer-Layout + Output-Formate für SysOps-Praxis)

- **`apps/typo3.py`: vier Composer-Mode-Sub-Layouts statt einem.**
  v0.0.7 nutzte nur `*/composer.json`-Glob (Top-Level), das verfehlt
  deployer.org-Style (composer.json in `<site>/current/`-Symlink) und
  DevOps-Konvention `typo3/<site>/composer.json` auf WordOps-Boxen.
  Live-Use-Case auf preprod.scheucherparkett.com zeigte `apps:[]`-Bug
  obwohl TYPO3 v11.5.42 installiert war (deployer-Layout `current →
  releases/65/composer.json`).

  **Erweiterung:** `_COMPOSER_JSON_GLOBS`-Tuple mit vier Patterns:
  ```
  "*/composer.json"               # Top-Level Mainstream
  "*/current/composer.json"       # Deployer-Style (atomic releases)
  "typo3/*/composer.json"         # DevOps-typo3-base Layout
  "typo3/*/current/composer.json" # typo3-base + Deployer
  ```

  Plus neuer Helper `_resolve_site_root(composer_json)` strippt die
  „current/"-Komponente bei Deployer-Layout, damit `AppInfo.path` den
  logischen Site-Root zeigt (statt flüchtigen `releases/<N>/`-Pfad).
  `config_file`-Feld zeigt Sub-Pattern implizit (z.B. `"composer.json"`
  bei Top-Level vs. `"current/composer.json"` bei Deployer).
  Quellen autoritativ: [deployer.org TYPO3-Recipe](https://deployer.org/docs/7.x/recipe/typo3)
  + DevOps' lokales Pattern aus typo3.update-Notes.

- **`commands/inventory.py`: zwei neue Output-Formate für SysOps-Praxis.**
  v0.0.7 hatte nur `rich` (Mensch-Tabellen) und `json` (AI-Agent).
  Reale DevOps-Workflows brauchen aber auch:

  - **`oneliner`** — Single-Line pipe-separated, copy-paste-friendly für
    Chat-Sharing (z.B. Hoster-Kommunikation, Schnell-Diagnose-Snapshot).
    Format: `schema:X|host:Y|os:Z|kernel:K|cc-suite:...|apps:...`
  - **`text`** — Plain multi-line (INI-artig, kein Rich-Markup) für
    File-Output + `cat`. Geeignet für SysOps-Doku + Run-Snapshots.

- **`commands/inventory.py`: neues `--output FILE` (`-o`)-Flag.**
  Schreibt Inventur in Datei statt stdout. Funktioniert mit allen
  Formaten (rich/json/oneliner/text). Rich-Output via
  `Console(file=fp, force_terminal=False, width=120)` für saubere
  ASCII-Tabellen in Datei (kein ANSI-Color-Bleed).

  **Beispiele:**
  ```
  cci inventory --format oneliner              # 1-Zeile copy-paste
  cci inventory --format text -o /tmp/inv.txt  # In Datei schreiben
  ```

### Tests

- 5 neue Cases in `test_typo3.py`:
  - `_resolve_site_root` strippt `current/`-Komponente
  - `_resolve_site_root` nimmt parent direkt
  - Deployer-Layout-Detection (current → releases/N/composer.json)
  - typo3-base-Layout-Detection (`/var/www/typo3/<site>/`)
  - typo3-base + Deployer kombiniert
- 63 → 68+ pytest grün erwartet.

### Pattern-Anker

Layout-Detection-Resilienz: ein Tool das nur EINE Layout-Pattern kennt
ist auf realen WordOps-Boxen blind. Multi-Pattern-Glob mit Site-Root-
Resolution ist defense-against-Drift. AI043's Live-Inspect auf osU2404
hat die Wurzel klar gezeigt (Memory-Anker: Live-Use-Case > theoretisches
Pattern, AI041-Schärfung 2026-05-12).

Output-Format-Pluralität: SysOps + DevOps + AI-Agent + Chat-Sharing
haben unterschiedliche Output-Bedürfnisse. Vier Formate (rich/json/
oneliner/text) statt Format-Monopol. Plus `--output FILE` für
File-Persistenz.

DevOps-Direktive 2026-05-12 (β-Routing): EIN-Sprint mit P0-MVP-Subset
(Deployer-Fix + Output-Formate) statt vier-Sprint-Plan. P1-Items
(WordOps-Detection, nginx in Stack, PHP-Multi-Version, Solr-robust)
bleiben Backlog für v0.0.9 oder spätere Session.

[0.0.8]: https://github.com/XED-dev/CCI/releases/tag/v0.0.8

## [0.0.7] — 2026-05-12

### Hinzugefügt (Help-UX-Korrektur + θ-Platzhalter)

- **`cli.py`: `-v` als Short-Form für `--version` (statt `-V`).**
  SysOps-Erwartung (DevOps-Direktive 2026-05-12): wenn `-V` belegt ist,
  ist `-v` aus User-Sicht ebenfalls belegt. Hauptbuchstabe-Variante macht
  semantisch keinen Unterschied — der User tippt `cci -v` und erwartet
  Version-Output. v0.0.6 hatte `-V` (Groß-V), Phase-G-Live-Test zeigte
  `cci -v` → „No such option: -v"-Error.

- **`cli.py`: `-h` als Alias für `--help` via Typer `context_settings`.**
  Mainstream-Bash-Idiomatik. Plus `cci --help | cci -h`-Hinweis im
  firstboot.sh Hint-Block sichtbar.

- **`commands/inventory.py`: docstring-Erweiterung mit Beispiel-Block.**
  Format folgt DevOps-Direktive 2026-05-12 — vier konkrete Inventur-
  Beispiele im `cci inventory --help`-Output sichtbar.

- **`cli.py`: `--dialog` / `-d` als hidden Platzhalter für Power-Dialog.**
  DevOps-Pattern-Anker 2026-05-12: künftige Power-Features (Version-
  Auswahl, Deinstall-Option, Verb-spezifische Detail-Inventur) sollen via
  `--dialog`/`-d`-Option erreichbar sein — NICHT im Haupt-Dialog.
  Mainstream-Alternative zu `--windy`/`-w` (deutsch-anglizistisch wachs-
  weich) oder `--power`/`-p` (zu generisch). `--dialog` semantisch klar
  für „dialog-style UIs". Aktuell `hidden=True` — Platzhalter für spätere
  v0.x-Implementations.

- **`firstboot.sh` VERSION sync mit Tool-Version** (0.0.6 → 0.0.7).
  Plus Hint-Block: `cci --help | cci -h` als Alias-Anzeige.

### Tests

- 2 neue Cases in `test_cli.py`: `-v`-Alias + `-h`-Alias.
- 78/78 pytest grün (76 + 2).

### Pattern-Anker

CLI-Short-Form-Konsistenz: wenn ein Buchstabe belegt ist, gilt er sowohl
als Klein- als auch Großvariante aus User-Sicht. Mainstream-Idiomatik
bevorzugt Kleinbuchstaben (`-v`, `-h`, `-d`) — Großbuchstaben nur für
disambiguierte Konflikt-Fälle. DevOps-Lehre 2026-05-12.

Power-Dialog-Pattern (`--dialog`/`-d`): minimal-Surface im Default-Dialog,
Power-Features hinter Opt-In-Flag. Plus Verb-spezifische Detail-Inventur
in v0.x via `cci inventory --dialog`. Skizze als hidden-Typer-Option
verewigt.

[0.0.7]: https://github.com/XED-dev/CCI/releases/tag/v0.0.7

## [0.0.6] — 2026-05-12

### Fixed (UX-Default-Korrektur + Ursachen-Phrase-Korrektur + Initial-Install-Pin)

- **`docs/firstboot.sh`: Default-Flip in User-Agency-Box — `[Y]` = Update
  auf latest (statt vorher `[Y]` = Keep installed).**
  v0.0.5 hatte als Default „Weitermachen mit installierter Version". Aber
  User-Intent von `bash <(curl)` ist „latest installieren". Wenn User Enter
  drückt (Default), bekam er die ALTE Version → User-Intent strukturell
  sabotiert. Bidirektional-Lehre: Bootstrap-Distribution-Pattern hat IMMER
  Default = „prominent latest", nie „mit installierter bleiben".

  **Korrektur:** `[Y]` = Update auf `v${latest}` (Default, empfohlen).
  `[k]` = Keep `v${installed}` (alte Version explizit behalten). `[n]` =
  Abbrechen. Unklare Auswahl → Safety-Default = Update (User-Intent-konform).

- **`docs/firstboot.sh`: Initial-Install mit Version-Pin (defensive).**
  `install_cci()` ruft jetzt zuerst `_pypi_latest_version()` und installiert
  `pipx install --force xed-cci==${latest}`. Fallback ohne Pin nur bei
  PyPI-API-Fail. User-Agency-Box triggert nur noch in Edge-Cases.

- **Ursachen-Phrase autoritativ korrigiert.**
  v0.0.5 nannte „PyPI-CDN-Stale + pipx-Resolver-Pinning". Das war spekulativ
  — `_pypi_latest_version()` hatte bewiesen dass PyPI korrekt latest meldete
  (kein CDN-Stale). Web-Recherche der pipx-CHANGELOG zeigte: **pipx 1.3.0
  (Februar 2024) erst implementierte „Force now implies --force-reinstall to
  pip arguments".** Ubuntu 22.04 Default ist pipx 1.0.0 (2022) — KEIN
  automatic --force-reinstall, pip kann lokale wheel-Cache reusen,
  `--no-cache-dir` bypasst nur HTTP-Cache.

  **Korrektur:** Box-Phrase + CHANGELOG verewigen autoritative Wurzel:
  „pipx < 1.3.0 fehlt automatic --force-reinstall (Ubuntu 22.04 Default)."

- **`firstboot.sh` VERSION sync mit Tool-Version** (0.0.5 → 0.0.6).

### Pattern-Anker (Lehr-Verkettung)

Bootstrap-Distribution-Pattern Default-Polarity: IMMER prominent „letzte
Version updaten" als Default, nie „mit installierter bleiben". User-Intent
von `bash <(curl)` ist „latest installieren" — Default muss diesem Intent
folgen, nie ihm widersprechen.

Investigations-Hierarchie-Anwendung: spekulative Ursachen-Phrasen niemals
in Code oder CHANGELOG verewigen. Web-Recherche zuerst, dann autoritative
Wurzel benennen. Falsche Diagnose-Phrase „PyPI-CDN-Stale" hat sich heute
durch v0.0.5-Box auf osU2404 als Live-Lüge gezeigt — Asche-Korrektur in
v0.0.6 mit autoritativer Wurzel aus pipx-CHANGELOG.

Power-User-Features (Version-Auswahl, Deinstall) gehören in Doku/Hilfe/
Support, NICHT in Haupt-Dialog. Minimal-Surface > Power-Features im
Bootstrap-Dialog (DevOps-Lehre 2026-05-12: „mehr Probleme als Lösungen").

[0.0.6]: https://github.com/XED-dev/CCI/releases/tag/v0.0.6

## [0.0.5] — 2026-05-12

### Hinzugefügt (SS7-Adaption: firstboot.sh User-Agency vs PyPI-CDN-Stale + pipx-Resolver-Pinning)

- **`docs/firstboot.sh`: nach pipx-Install vergleicht das Skript installed-
  Version mit PyPI-latest-Version. Bei Divergenz: User-Agency-Prompt mit
  Versions-Box + Optionen [Y/r/n].**
  Live-Use-Case auf osU2404 (Ubuntu 22.04, pipx 1.0.0): `pipx install --force
  xed-cci` reinstalliert ins existing venv MIT DERSELBEN Version (0.0.2)
  statt PyPI-latest (0.0.4) zu pullen — pipx-1.0.0-`--force`-Semantik nimmt
  existing-venv-Metadata als Resolver-Input. Plus PyPI-Fastly-CDN-Stale-
  Backend kann ähnliche Symptome bei frisch-uploaded Versionen zeigen.
  v0.0.4-Fix (`--force`) löste pipx-list-short-Bug, nicht den `--force`-
  Same-Version-Bug.

  **Lösung:** SS7-Vision aus AI040 für ccc-bootstrap-system Layer-adaptiert
  für firstboot.sh-Bash. Pattern: „System lügt nicht statt Cache-Hide-Magie."
  Nach Install macht `verify_version_with_user_agency()`:
  1. `pipx list --json` für installed-Version-Extraktion (Stdlib-only via
     python3-Heredoc — pipx-1.0.0 hat `--json`, nicht `--short`)
  2. PyPI JSON API für latest-Version (`curl + python3 -c "json.load"`)
  3. Defense-Recovery bei curl-Fail oder JSON-Decode-Fail: weiter mit
     installed-Version, Warning loggen — kein Block
  4. Bei Match: OK-Marker
  5. Bei Divergenz: Versions-Box + 3 Optionen:
     - **[Y]** Weitermachen (Default, Safety-Default-Pattern)
     - **[r]** Retry mit Version-Pin: `pipx install --force xed-cci==${latest}`
       — explicit-Version-Pin umgeht pipx-1.0.0-`--force`-Same-Version-Bug
       (Empirik-getriebene Schärfung)
     - **[n]** Abbrechen
  6. Max-5-Retries-Cap gegen Infinite-Loop

- **`firstboot.sh` VERSION-Konstante sync mit Tool-Version** (0.0.4 → 0.0.5).

### Pattern-Anker

Vision-Patterns sind Layer-agnostic, Implementations sind Layer-spezifisch.
SS7-Wurzel (User-Agency vs Hidden-Retry-Magie) bleibt invariant über Tool-
Layer-Grenzen — Bash-Bootstrap vs Python-Verb. Implementations-Variante folgt
Layer-Konstraints (Bash `read -p` statt Whiptail; python3-Heredoc statt jq).

Bidirektional-Lehre für AI-Agents: Self-Healing-Workflow > Workaround als
Default. Workaround NUR wenn Self-Healing-Workflow nachweislich gescheitert
— sonst verliert man Test-Chance + Diagnose-Quelle. Empirik (Phase-G v0.0.4-
Live-Test) gibt Sprint-Priorität-Klärung > theoretische Pattern-Bewertung.

Plus Symptom-Fix-Loop-Detection: wenn 3+ Sprints kurz hintereinander dasselbe
Layer touchen, ist die Wurzel woanders. Strukturelle Lösung (User-Agency)
schlägt Pattern-Switching (--force vs upgrade-or-install).

[0.0.5]: https://github.com/XED-dev/CCI/releases/tag/v0.0.5

## [0.0.4] — 2026-05-12

### Fixed (firstboot.sh pipx-Upgrade-Pfad)

- **`docs/firstboot.sh`: `bash <(curl)` installiert jetzt wirklich latest.**
  Bisher prüfte `install_cci()` mit `pipx list --short 2>/dev/null | grep -q
  '^xed-cci '` ob xed-cci installiert ist und wählte upgrade-or-install-Pfad.
  Live-Use-Case auf Ubuntu 22.04 jammy (pipx 1.0.0 Default) zeigte: pipx 1.0.0
  hat kein `--short`-Flag → command failt → stderr unterdrückt → grep returnt
  False → else-Branch → `pipx install` → „already installed, no modification"
  → kein Upgrade durchgeführt. Self-Healing-Pattern war strukturell verletzt
  auf älteren pipx-Versionen.

  **Fix:** 3-Zeilen-Refactor zu bedingungslosem `pipx install --force xed-cci
  --pip-args="--no-cache-dir"`. Pipx-version-unabhängig + Support-tauglich +
  Re-Install <1 Min toleriert per DevOps-Direktive.

  Plus `firstboot.sh` VERSION-Konstante sync mit Tool-Version (0.0.1 → 0.0.4)
  für klare Release-Korrelation.

### Pattern-Anker

Bootstrap-Distribution-Pattern für Tool-Updates: `pipx install --force` über
Detection-Pattern. Support-Garantie ist Hard-Requirement — der User-Intent
„curl-Befehl = immer neueste Version" + die Support-Verlässlichkeit
„`bash <(curl)` installiert wirklich latest" wiegen mehr als Idempotenz-
Eleganz + Performance-Optimierung. Detection-Pattern bleibt scharf für andere
Use-Cases (Filesystem-Marker > CLI-Output-Parse), aber für Bootstrap-
Distribution ist `--force` strukturell support-tauglich.

Bidirektional-Lehre für AI-Agents: bei Memory-kanonischen Patterns IMMER
Live-Use-Case-Verify einbauen — Self-Healing-Pattern ist nur theoretisch
wirksam, faktische Wirksamkeit braucht pipx-Version-Compat-Verify.

[0.0.4]: https://github.com/XED-dev/CCI/releases/tag/v0.0.4

## [0.0.3] — 2026-05-12

### Hinzugefügt (TYPO3 Composer-Mode-Detection)

- **`apps/typo3.py`: cci erkennt jetzt TYPO3-Sites im Composer-Mode (v11+).**
  Bisher fand der TYPO3-Detector nur Classic-Mode-Sites (`typo3conf/
  LocalConfiguration.php` unter `*/htdocs/` oder `*/`). Live-Use-Case auf
  einer Multi-Site-Box mit TYPO3 v11+ Composer-Layout zeigte `apps: []`-
  Inventur trotz vorhandener TYPO3-Installation (Web-Root in `<site>/
  public/`, Project-Root mit `composer.json`).

  **Erweiterung:** Composer-Mode-Detection ZUERST, Classic-Mode-Detection
  als Backward-Compat-Fallback. Composer-Detection: Glob `*/composer.json`
  + Filter auf `typo3/cms-core`-Dependency. Version-Extraktion in drei
  Stufen: (a) `vendor/typo3/cms-core/Classes/Information/Typo3Version.php`
  (Standard wenn `vendor/` installiert), (b) `composer.lock` mit
  `packages[].name == typo3/cms-core` (Fallback wenn `vendor/` fehlt),
  (c) `'unknown'`. Layout verifiziert via WebFetch docs.typo3.org.

- **`_types.py`: neues Feld `mode: Literal["composer", "classic"]` in `AppInfo`.**
  AI-Agent-Konsumtion: Composer-vs-Classic-Sicht für Fleet-weite Update-
  Empfehlungen ohne config_file-Suffix-Parsing. Schema-Versionierung bleibt
  `0.0.1` (additive Erweiterung, kein Breaking Change).

### Tests

- 13 neue Cases in `test_typo3.py` (3 für `_is_typo3_composer_project` +
  3 für `_parse_typo3_version_from_lockfile` + 4 für `detect_typo3`
  Composer-Mode + 1 Multi-Mode-Integration + 2 existing-Anpassungen mit
  `mode`-Assert).

### Pattern-Anker

Live-Use-Case-Bug → Tool-Sprint > Workaround. Detection-Limit im Tool
während heißer Anwendung sofort fixen, nicht in Backlog vertagen. Self-
Heal-Loop zwischen Tool und realer Anwendung als Default, nicht Reaktion.

[0.0.3]: https://github.com/XED-dev/CCI/releases/tag/v0.0.3

## [0.0.2] — 2026-05-09

### Fixed (PIPX_HOME-env-Drift)

- **`cc_suite.py`: cci sieht jetzt seine eigene system-wide pipx-Installation.**
  Bisher fielen alle drei CC-Suite-Versionen (`xed-ccc`/`xed-cca`/`xed-cci`)
  auf `'unknown'` weil `cci`-runtime ohne expliziten `PIPX_HOME` startet
  und pipx die user-default-Pfade (`~/.local/share/pipx/`) durchsucht
  statt der system-wide-Installation in `/opt/pipx/` (von `firstboot.sh`
  gesetzt).

  **Fix:** Auto-Detection via `sys.executable`-Walk. `_detect_pipx_home()`
  identifiziert PIPX_HOME aus dem Pfad-Prefix vor `venvs/`-Segment
  (z.B. `/opt/pipx/venvs/xed-cci/bin/python3` → `/opt/pipx`).
  `collect_cc_suite_info()` setzt env-Override mit detected PIPX_HOME
  beim subprocess-Aufruf an pipx. Bei dev-uv-venvs (kein `venvs/`-Segment)
  bleibt env=None, Parent-Env wird inherited (Workstation-Live-Smoke
  weiterhin grün).

  Detection ist robust gegen Symlinks: `sys.executable` ist UNRESOLVED
  per PEP-405, Walk via `Path.parents` findet `venvs/` ohne explizit
  `.resolve()` (Symlink-Risiko-Mitigation dokumentiert).

### Diagnose-Pfad

Bug entdeckt im SS7-Live-Test auf 5521-pmDESK durch DevOps + AI039.
Workstation-Schema-Verify (`pipx list --json` Sample) bestätigte: cci's
Parse-Pfad `venvs[name].metadata.main_package.package_version` ist
korrekt für pipx 1.x. Wurzel war NICHT Schema-Drift sondern PIPX_HOME-
env-Drift zwischen install-time und runtime. Bidirektional-Sparring-
Pfad: AI039-Diagnose-Skizze → AI040-Workstation-Verify → Hypothesen-
Triage → AI039-Approach-Wahl (δ Auto-Detect) → AI040-Implementation.

### Tests

- 5 neue Cases in `test_cc_suite.py` für `_detect_pipx_home` (system-wide,
  user-default, dev-venv-None) + `collect_cc_suite_info` env-Argument-
  Verify (mit + ohne PIPX_HOME).
- 65/65 pytest grün — keine Regression bei existing 60 Cases.

[0.0.2]: https://github.com/XED-dev/CCI/releases/tag/v0.0.2

## [0.0.1] — 2026-05-08

### Hinzugefügt (CCI-SS1 — Skelett-Setup)

- **CLI-Skelett** mit Typer-app + `--version`/`-V`-Flag + `--help`-Übersicht
- **`cci inventory` als Stub-Verb** — Skelett-Form, eigentliche Implementation
  folgt in SS5 (Composition + Rich + JSON-Output + `--section`-Filter)
- **pyproject.toml** mit hatchling-Backend + dynamic version aus
  `_version.py` + Stack-Konsistenz zu ccc/cca (Typer + Rich + psutil + pytest)
- **Test-Skelett** mit 3 Smoke-Cases (--version, --help, inventory-Stub)

### Architektur-Notizen

- Phase 1: Python-CLI Read-Only-Klasse, Drei-Tool-Suite-Symmetrie zu ccc + cca
- Phase 2 (DeltaChat-Bot) + Phase 3 (cBOX@ /Monitor) sind Vision/Mission,
  NICHT in dieser Version umgesetzt — siehe `WHITEPAPER.md` für vollständige
  Architektur-Entscheidungsfindung
- Symmetrisches Layout: `docs/firstboot.sh` (Pages-Source), kein `scripts/`-
  Pfad-Mapping (Lehre aus CCC-Layout-Refactor 2026-05-08)
- Read-Only-Garantie strukturell via `safe_run.py` (kommt SS2)

[0.0.1]: https://github.com/XED-dev/CCI/releases/tag/v0.0.1

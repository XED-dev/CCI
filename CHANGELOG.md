# Changelog

Alle bemerkenswerten Änderungen an `xed-cci` werden hier dokumentiert.

Format folgt [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/).

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

# Changelog

Alle bemerkenswerten Änderungen an `xed-cci` werden hier dokumentiert.

Format folgt [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/).

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

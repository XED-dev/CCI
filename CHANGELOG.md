# Changelog

Alle bemerkenswerten Änderungen an `xed-cci` werden hier dokumentiert.

Format folgt [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/).

## [0.0.1] — UNRELEASED

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

# XED /CCI — cBOX@ /Container Inventur

> Read-Only-Tool für lokale Box-Klassen-Inventur. Drittes Mitglied der XED /CC-Suite
> neben [ccc](../XED-CCC/) (Control) und [cca](../XED-CCA/) (App-Installation).

**100% Read-Only:** cci verändert NIEMALS den Box-Zustand. Strukturelle
Garantie via subprocess-Whitelist.

## Was es macht (Phase 1, v0.0.9+)

`cci typo3` liefert eine vollständige Inventur einer WordOps-LEMP-Ubuntu-LTS-Box
mit TYPO3-Composer + optional Apache Solr — als Rich-Tabelle (Mensch) oder JSON
(AI-Agent-Konsumtion).

**Sektionen:**
- **OS** — `/etc/os-release` + Kernel
- **CC-Suite** — installed `xed-ccc` / `xed-cca` / `xed-cci`-Versionen
- **Stack** — `python3` / `php` / `node` Versionen (wenn installiert)
- **Databases** — `mysql` / `mariadb` / `postgres` Versionen + Service-Status
- **Sites** — TYPO3-Sites pro Domain mit Pfaden + Versionen + Modus

## Box-Klassen

Verb-basierte Subkommandos pro Box-Klasse:

| Verb | Box-Klasse |
|---|---|
| `cci typo3` | WordOps-LEMP-Ubuntu-LTS + TYPO3-Composer + ADD-ONs (z.B. Apache Solr) |

Perspektivisch weitere Box-Klassen (`cci wordpress`, ...) als eigene Top-Level-Verben.

## Installation

**Empfohlen** — auf einer cBOX (LXC) via firstboot.sh:

```bash
bash <(curl -s https://cci.xed.dev/firstboot.sh)
```

Das Script installiert Python-Stack + pipx und holt `xed-cci` von PyPI.

**Manuell** — wenn pipx schon vorhanden:

```bash
pipx install xed-cci
```

## Verwendung

```bash
# Komplette Inventur als Rich-Tabelle
cci typo3

# JSON für AI-Agent-Konsumtion
cci typo3 --format json

# Gefilterte Sektion
cci typo3 --section os
cci typo3 --section sites
cci typo3 --section stack
cci typo3 --section databases
cci typo3 --section cc-suite

# Output-Formate
cci typo3 --format oneliner              # 1-Zeile pipe-separated (Chat-Sharing)
cci typo3 --format text -o /tmp/inv.txt  # Plain multi-line in Datei

# Box-Klassen-Übersicht
cci --help

# Tool-Version
cci --version
```

## Use-Case: AI-Agent-Konsultation

```bash
cci typo3 --format json > /tmp/box.json

# Dann an AI-Agent (Claude Code, ChatGPT, etc.):
# "Hier ist meine Box-Inventur. Passt diese Konfiguration für Typo3 v13?
#  Welche Anpassungen sind nötig?"
```

Der AI-Agent sieht in einem strukturierten JSON-Block alle relevanten
Box-Daten und kann fundierte Migrations-/Update-Empfehlungen geben.

## v0.0.9 BREAKING-Migration

- **Verb-Switch:** `cci inventory` → `cci typo3` (hartgesetzt, kein Deprecation-Alias).
- **Section-Rename:** `--section apps` → `--section sites`.
- **JSON-Schema 0.0.1 → 0.0.2:** Top-Level-Key `"apps"` → `"sites"`. AI-Agent-
  Konsumenten und Skripte mit `report["apps"]` müssen auf `report["sites"]`
  umgestellt werden. Detector-Layer-Code (`AppInfo` + `collect_apps_info`) bleibt
  unverändert.

Siehe [CHANGELOG.md](./CHANGELOG.md) für vollständige BREAKING-Liste + Verb-Mapping.

## Roadmap

- **Phase 1 (jetzt):** Python-CLI mit Box-Klassen-Subkommandos (`cci typo3`,
  perspektivisch `cci wordpress` u.a.), read-only, pipx-Distribution,
  ccc/cca-Pattern-Symmetrie.
- **Phase 2 (Vision):** DeltaChat-Bot-Daemon für dezentrale Box-Steuerung
  ohne offene Ports + TLS-Cert-Management.
- **Phase 3 (Vision):** cBOX@ /Monitor Master-Programm für Inventur-
  Aggregation über tausende cBOX@ /CUBE-Boxen.

Detaillierte Architektur-Entscheidungsfindung + Vision/Mission kommt
zukünftig in das [Github Wiki](https://github.com/XED-dev/CCI/wiki)
und/oder ins [Collective-Context-Forum](https://collective-context.org/).

## Lizenz

MIT

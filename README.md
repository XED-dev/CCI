# XED /CCI — cBOX@ /Container Inventur

> Read-Only-Tool für lokale cBOX-Inventur. Drittes Mitglied der XED /CC-Suite
> neben [ccc](../XED-CCC/) (Control) und [cca](../XED-CCA/) (App-Installation).

**100% Read-Only:** cci verändert NIEMALS den Box-Zustand. Strukturelle
Garantie via subprocess-Whitelist.

## Was es macht (Phase 1)

`cci inventory` liefert eine vollständige Inventur der lokalen Box als
Rich-Tabelle (Mensch) oder JSON (AI-Agent).

**Sektionen:**
- **OS** — `/etc/os-release` + Kernel
- **CC-Suite** — installed `xed-ccc` / `xed-cca` / `xed-cci`-Versionen
- **Stack** — `python3` / `php` / `node` Versionen (wenn installiert)
- **Databases** — `mysql` / `mariadb` / `postgres` Versionen + Service-Status
- **Apps** — Server-Apps mit Pfaden + Versionen (v0.0.1: Typo3-Detection)

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
cci inventory

# JSON für AI-Agent-Konsumtion
cci inventory --format json

# Gefilterte Sektion
cci inventory --section os
cci inventory --section apps
cci inventory --section stack
cci inventory --section databases
cci inventory --section cc-suite

# Verb-Übersicht
cci --help

# Tool-Version
cci --version
```

## Use-Case: AI-Agent-Konsultation

```bash
cci inventory --format json > /tmp/box.json

# Dann an AI-Agent (Claude Code, ChatGPT, etc.):
# "Hier ist meine Box-Inventur. Passt diese Konfiguration für Typo3 v13?
#  Welche Anpassungen sind nötig?"
```

Der AI-Agent sieht in einem strukturierten JSON-Block alle relevanten
Box-Daten und kann fundierte Migrations-/Update-Empfehlungen geben.

## Roadmap

- **Phase 1 (jetzt):** Python-CLI mit `cci inventory`-Verb (read-only,
  pipx-Distribution, ccc/cca-Pattern-Symmetrie). Erste App-Detection für
  Typo3.
- **Phase 2 (Vision):** DeltaChat-Bot-Daemon für dezentrale Box-Steuerung
  ohne offene Ports + TLS-Cert-Management. Siehe
  [WHITEPAPER.md §Phase 2](./WHITEPAPER.md#phase-2--deltachat-bot-daemon-visionmission-nicht-für-phase-1-umsetzen).
- **Phase 3 (Vision):** cBOX@ /Monitor Master-Programm für Inventur-
  Aggregation über tausende cBOX@ /CUBE-Boxen. Siehe
  [WHITEPAPER.md §Phase 3](./WHITEPAPER.md#phase-3--cbox-monitor-visionmission-nicht-für-phase-12-umsetzen).

Volle Architektur-Entscheidungsfindung + Vision/Mission siehe
[WHITEPAPER.md](./WHITEPAPER.md).

## Lizenz

MIT

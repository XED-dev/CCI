#!/bin/bash
# firstboot.sh v0.0.5 — XED /CCI cBOX@ /Container Inventur Bootstrap
#
# Quelle:    https://github.com/XED-dev/CCI
# Aufruf:    bash <(curl -s https://cci.xed.dev/firstboot.sh)
# Lokal:     bash firstboot.sh
#
# Was es tut (~210 Zeilen, schmal weil cci Read-Only-Tool ist):
#   Phase 0   — Pre-Flight (root + distro + Audit-Log-Init)
#   Phase 1   — apt install Python-Stack + pipx (Phased-Updates-Bypass)
#   Phase 2   — pipx install xed-cci (--force, no-cache-dir Bypass)
#   Phase 2.5 — Version-Verify mit User-Agency vs PyPI-CDN-Stale (SS7)
#   Phase 3   — PATH-Fix (pct-enter-Falle)
#   Phase 4   — Hint-Block (cci inventory-Verben)
#
# cci ist Read-Only — KEIN bootstrap-system-Verb wie ccc/cca, KEIN
# apply-Phase. firstboot.sh ist „install + verify + first-run-info" minimal.
#
# Lizenz: MIT (siehe LICENSE im XED-dev/CCI-Repo)

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# === Globals ===

VERSION="0.0.5"
SCRIPT_NAME="firstboot.sh"
FIRSTBOOT_LOG_FILE="/var/log/xed-cci.log"

PIPX_HOME_DIR="/opt/pipx"
PIPX_BIN_DIR_PATH="/usr/local/bin"

PYPI_API_URL="https://pypi.org/pypi/xed-cci/json"
VERIFY_MAX_RETRIES=5

# === Output-Helpers + Audit-Log ===

# Audit-Log-Format identisch zu ccc/cca audit_log:
# '<ISO-UTC> [LEVEL] message' — grep-Pipelines arbeiten ueber alle drei
# CC-Suite-Tools auf konsistentem Format.
log_to_file() {
    local level="$1"; shift
    [ -n "${FIRSTBOOT_LOG_FILE:-}" ] || return 0
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [$level] $*" >> "$FIRSTBOOT_LOG_FILE" 2>/dev/null || true
}

init_log_file() {
    [ -n "${FIRSTBOOT_LOG_FILE:-}" ] || return 0
    mkdir -p "$(dirname "$FIRSTBOOT_LOG_FILE")" 2>/dev/null || true
    {
        echo ""
        echo "================================================================"
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [INIT] firstboot.sh v${VERSION} run start"
        echo "================================================================"
    } >> "$FIRSTBOOT_LOG_FILE" 2>/dev/null || true
}

err()  { echo "ERROR: $*" >&2; log_to_file "ERROR" "$*"; }
warn() { echo "⚠ $*"; log_to_file "WARN" "$*"; }
info() { echo "→ $*"; log_to_file "INFO" "$*"; }
ok()   { echo "✔ $*"; log_to_file "OK" "$*"; }

banner() {
    echo
    echo "================================================================"
    echo "  cBOX@ /Container Inventur — ${SCRIPT_NAME} v${VERSION}"
    echo "  Read-Only-Tool für lokale cBOX-Inventur"
    echo "  cBOX.at/YOU by XED.dev Tools via Collective Context (CC)"
    echo "================================================================"
    echo
}

# === Phase 0 — Pre-Flight ===

require_root() {
    if [ "$(id -u)" -ne 0 ]; then
        err "Skript muss als root laufen. Tipp: sudo bash $0"
        exit 1
    fi
}

require_supported_distro() {
    if [ ! -r /etc/os-release ]; then
        err "/etc/os-release nicht lesbar — unbekannte Distro."
        exit 1
    fi
    # shellcheck disable=SC1091
    . /etc/os-release
    case "${ID:-}" in
        debian|ubuntu) ok "Distro erkannt: ${PRETTY_NAME:-$ID}" ;;
        *) err "Distro '${ID:-unknown}' nicht unterstuetzt — nur Debian/Ubuntu."; exit 1 ;;
    esac
}

# === Phase 1 — apt install Python-Stack + pipx ===

bootstrap_apt() {
    info "apt update + Python-Stack + pipx installieren..."
    apt-get update -qq </dev/null
    # APT::Get::Always-Include-Phased-Updates=true: Ubuntu 24.04+ rollt
    # Updates wellenweise aus. Ohne Flag werden phased Pakete still
    # skipped (Memory-Anker reference_apt_phased_updates.md, in xed-ccc
    # SS6.6 v0.2.2 strukturell verewigt).
    apt-get -o APT::Get::Always-Include-Phased-Updates=true install \
        -y -qq --no-install-recommends \
        python3 python3-venv pipx ca-certificates curl </dev/null

    if ! command -v pipx >/dev/null 2>&1; then
        err "pipx nicht verfuegbar nach Install — Bootstrap fehlgeschlagen."
        exit 1
    fi
    ok "Python-Stack bereit: pipx $(pipx --version 2>&1 | head -1)"
}

# === Phase 2 — pipx install xed-cci ===

install_cci() {
    export PIPX_HOME="$PIPX_HOME_DIR"
    export PIPX_BIN_DIR="$PIPX_BIN_DIR_PATH"

    # Bootstrap-Distribution-Pattern: pipx install --force xed-cci. Support-
    # Garantie ist Hard-Requirement + pipx-version-unabhaengig. --no-cache-dir
    # bypasst lokalen pip-HTTP-Cache als defense-in-depth.
    info "xed-cci via pipx (install --force, no-cache-dir)..."
    pipx install --force xed-cci --pip-args="--no-cache-dir"
    ok "xed-cci installiert via pipx"

    # SS7-Adaption: User-Agency vs PyPI-CDN-Stale + pipx-Resolver-Pinning.
    # pipx 1.0.0 --force ohne Version-Pin nimmt existing-venv-Metadata als
    # Resolver-Input statt PyPI-latest — silent-fail-Risiko. verify-Funktion
    # macht die Divergenz transparent + gibt User-Agency statt Hidden-Magie.
    verify_version_with_user_agency
}

# === Phase 2.5 — Version-Verify mit User-Agency (SS7) ===

# Pattern-Anker: „System luegt nicht statt Cache-Hide-Magie."
# Nach pipx-Install vergleicht das Skript installed-Version mit PyPI-latest.
# Bei Divergenz: User-Agency-Prompt mit Versions-Box + 3 Optionen [Y/r/n].
# Max-Retries-Cap gegen Infinite-Loop. Defense-Recovery bei Check-Failure.

_pipx_installed_version() {
    # Stdlib-Reflex: python3 ist nach Phase-1-apt verfuegbar.
    # pipx 1.0.0 hat --json, nicht --short (Live-Lehre aus v0.0.4-Bug).
    pipx list --json 2>/dev/null | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin)['venvs']['xed-cci']['metadata']['main_package']['package_version'])
except (KeyError, json.JSONDecodeError):
    pass
" 2>/dev/null
}

_pypi_latest_version() {
    # PyPI JSON API: https://docs.pypi.org/api/json/
    # User-Agent setzen (PyPI-Best-Practice fuer Consumer-Identification).
    # --max-time gegen Hang bei Netzwerk-Failure.
    curl -sSf --max-time 10 \
        -H "User-Agent: xed-cci-firstboot/${VERSION}" \
        "${PYPI_API_URL}" 2>/dev/null | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin)['info']['version'])
except (KeyError, json.JSONDecodeError):
    pass
" 2>/dev/null
}

verify_version_with_user_agency() {
    local retry_count=0
    while true; do
        local installed latest
        installed=$(_pipx_installed_version)
        latest=$(_pypi_latest_version)

        # Defense-Recovery: bei Check-Failure einfach weiter (kein Block).
        if [ -z "$installed" ]; then
            warn "Installed-Version-Check failed — weiter ohne Verify."
            return 0
        fi
        if [ -z "$latest" ]; then
            warn "PyPI-Check failed (Netzwerk/Timeout) — weiter mit installed v${installed}."
            return 0
        fi

        # Match — OK.
        if [ "$installed" = "$latest" ]; then
            ok "Version-Match: v${installed} (installed = PyPI latest)"
            return 0
        fi

        # Versions-Divergenz — User-Agency.
        echo
        echo "  ┌─ Versions-Divergenz ──────────────────────────────────────┐"
        printf "  │ Installiert: v%-44s│\n" "${installed}"
        printf "  │ PyPI latest: v%-44s│\n" "${latest}"
        echo "  │ Ursache: PyPI-CDN-Stale + pipx-Resolver-Pinning.           │"
        echo "  └────────────────────────────────────────────────────────────┘"
        echo
        echo "  [Y] Weitermachen mit v${installed}  (Default)"
        if [ "$retry_count" -lt "$VERIFY_MAX_RETRIES" ]; then
            echo "  [r] Retry mit Version-Pin: pipx install --force xed-cci==${latest}  (${retry_count}/${VERIFY_MAX_RETRIES})"
        fi
        echo "  [n] Abbrechen"
        echo
        local response=""
        read -r -p "  Auswahl [Y/r/n]: " response
        case "${response:-Y}" in
            [Yy])
                ok "User-Wahl: weiter mit v${installed}."
                return 0
                ;;
            [Rr])
                if [ "$retry_count" -ge "$VERIFY_MAX_RETRIES" ]; then
                    info "Max-Retries (${VERIFY_MAX_RETRIES}) erreicht — weiter mit v${installed}."
                    return 0
                fi
                retry_count=$((retry_count + 1))
                info "Retry ${retry_count}/${VERIFY_MAX_RETRIES}: pipx install --force xed-cci==${latest}..."
                # Version-Pin umgeht pipx-1.0.0 --force-Same-Version-Bug
                # (Live-Lehre osU2404 2026-05-12).
                pipx install --force "xed-cci==${latest}" --pip-args="--no-cache-dir"
                ;;
            [Nn])
                err "User-Wahl: Abbrechen."
                exit 1
                ;;
            *)
                ok "Unklare Auswahl '${response}' — Safety-Default [Y]: weiter mit v${installed}."
                return 0
                ;;
        esac
    done
}

# === Phase 3 — PATH-Fix (pct-enter-Falle) ===

# pct enter startet NON-LOGIN interactive bash mit minimal-PATH ohne
# /usr/local/bin. /etc/bash.bashrc fuer non-login + /etc/profile.d/ fuer
# login. Pattern aus xed-ccc.
setup_path_fix() {
    cat > /etc/profile.d/xed-cci.sh <<'EOF'
# XED-CCI: stelle sicher dass /usr/local/bin im PATH ist (Login-Shells).
case ":$PATH:" in
    *":/usr/local/bin:"*) ;;
    *) export PATH="/usr/local/bin:$PATH" ;;
esac
EOF
    chmod 0644 /etc/profile.d/xed-cci.sh

    if ! grep -q '# XED-CCI PATH-Fix' /etc/bash.bashrc 2>/dev/null; then
        cat >> /etc/bash.bashrc <<'EOF'

# XED-CCI PATH-Fix (interactive non-login bash, z.B. pct enter)
case ":$PATH:" in
    *":/usr/local/bin:"*) ;;
    *) export PATH="/usr/local/bin:$PATH" ;;
esac
EOF
    fi
    ok "PATH-Fix gesetzt (/etc/profile.d + /etc/bash.bashrc)."
}

# === Phase 4 — Hint-Block (Wartungs-Pfad sichtbar machen) ===

show_hint() {
    echo
    echo "→ Naechste Schritte (Read-Only-Inventur):"
    echo
    echo "    cci inventory                     # Komplette Inventur (Rich)"
    echo "    cci inventory --format json       # JSON fuer AI-Agent"
    echo "    cci inventory --section os        # Nur OS-Sektion"
    echo "    cci inventory --section apps      # Nur Server-Apps"
    echo "    cci --help                        # Verb-Uebersicht"
    echo
    echo "→ Audit-Log dieses Bootstrap-Runs: ${FIRSTBOOT_LOG_FILE}"
    echo "    tail -50 ${FIRSTBOOT_LOG_FILE}"
    echo
}

# === Main ===

main() {
    banner
    require_root
    init_log_file
    require_supported_distro
    bootstrap_apt
    install_cci
    setup_path_fix
    show_hint
}

main "$@"

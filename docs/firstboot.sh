#!/bin/bash
# firstboot.sh v0.0.7 — XED /CCI cBOX@ /Container Inventur Bootstrap
#
# Quelle:    https://github.com/XED-dev/CCI
# Aufruf:    bash <(curl -s https://cci.xed.dev/firstboot.sh)
# Lokal:     bash firstboot.sh
#
# Was es tut (~230 Zeilen, schmal weil cci Read-Only-Tool ist):
#   Phase 0   — Pre-Flight (root + distro + Audit-Log-Init)
#   Phase 1   — apt install Python-Stack + pipx (Phased-Updates-Bypass)
#   Phase 2   — pipx install xed-cci mit Version-Pin (latest from PyPI)
#   Phase 2.5 — Version-Verify-Edge-Cases mit User-Agency (SS7)
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

VERSION="0.0.7"
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

# === Phase 2.5 helpers — Version-Quellen ===

# Pre-definiert vor install_cci() weil Initial-Install latest aus PyPI braucht.
# Stdlib-Reflex: python3 ist nach Phase-1-apt verfuegbar.

_pipx_installed_version() {
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

# === Phase 2 — pipx install xed-cci mit Version-Pin ===

install_cci() {
    export PIPX_HOME="$PIPX_HOME_DIR"
    export PIPX_BIN_DIR="$PIPX_BIN_DIR_PATH"

    # Bootstrap-Distribution-Pattern: Initial-Install mit Version-Pin via
    # PyPI-API-Query. Pin umgeht pipx < 1.3.0 fehlendes automatic
    # --force-reinstall-Forwarding (Ubuntu 22.04 Default ist pipx 1.0.0).
    # Quelle: pipx CHANGELOG (https://pipx.pypa.io/stable/changelog/) —
    # „pipx 1.3.0 (Feb 2024): Force now implies --force-reinstall to pip".
    # Fallback ohne Pin bei PyPI-Check-Fail — User-Agency-Box catches up.
    local latest
    latest=$(_pypi_latest_version)
    if [ -n "$latest" ]; then
        info "xed-cci via pipx install --force xed-cci==${latest}..."
        pipx install --force "xed-cci==${latest}" --pip-args="--no-cache-dir"
    else
        info "xed-cci via pipx install --force (PyPI-Check failed, Fallback ohne Pin)..."
        pipx install --force xed-cci --pip-args="--no-cache-dir"
    fi
    ok "xed-cci installiert via pipx"

    # SS7-Adaption: User-Agency-Box bei Edge-Cases (z.B. Initial-Pin failed
    # weil PyPI-API down war, oder PyPI-Drift zwischen Install und Verify).
    # System luegt nicht statt Cache-Hide-Magie.
    verify_version_with_user_agency
}

# === Phase 2.5 — Version-Verify mit User-Agency (SS7) ===

# Pattern-Anker: „System luegt nicht statt Cache-Hide-Magie."
# Default ist IMMER Update auf PyPI-latest (User-Intent von `bash <(curl)`).
# [k] erlaubt User explizit „bei installierter bleiben". [n] abbrechen.
# Max-Retries-Cap gegen Infinite-Loop. Defense-Recovery bei Check-Failure.

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

        # Max-Retries erreicht — Resignation mit Warning (System luegt nicht).
        if [ "$retry_count" -ge "$VERIFY_MAX_RETRIES" ]; then
            warn "Max-Retries (${VERIFY_MAX_RETRIES}) erreicht — installed v${installed} bleibt (PyPI latest waere v${latest})."
            return 0
        fi

        # Versions-Divergenz — User-Agency mit Default=Update.
        echo
        echo "  ┌─ Versions-Divergenz ──────────────────────────────────────┐"
        printf "  │ Installiert: v%-44s│\n" "${installed}"
        printf "  │ PyPI latest: v%-44s│\n" "${latest}"
        echo "  │ Ursache: pipx < 1.3.0 fehlt automatic --force-reinstall.  │"
        echo "  └───────────────────────────────────────────────────────────┘"
        echo
        echo "  [Y] Auf v${latest} updaten  (Default — empfohlen)"
        echo "  [k] Bei v${installed} bleiben"
        echo "  [n] Abbrechen"
        echo
        local response=""
        read -r -p "  Auswahl [Y/k/n]: " response
        case "${response:-Y}" in
            [Kk])
                ok "User-Wahl [k]: bei v${installed} bleiben."
                return 0
                ;;
            [Nn])
                err "User-Wahl [n]: Abbrechen."
                exit 1
                ;;
            *)
                # Default + unklare Auswahl → Update (User-Intent-konform).
                retry_count=$((retry_count + 1))
                info "Update ${retry_count}/${VERIFY_MAX_RETRIES}: pipx install --force xed-cci==${latest}..."
                pipx install --force "xed-cci==${latest}" --pip-args="--no-cache-dir"
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
    echo "    cci --help | cci -h               # Verb-Uebersicht"
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

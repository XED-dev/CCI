"""safe_run — Whitelist-only subprocess für Read-Only-Garantie.

cci ist Read-Only by structural design: jeder subprocess-Aufruf MUSS
gegen die `COMMAND_WHITELIST` geprüft sein. Bei Verstoß wird
`ReadOnlyViolationError` geworfen — strukturelle Sicherheit gegen
versehentliche Box-State-Mutation.

Lakmus-Test pro Helper (siehe WHITEPAPER §Read-Only-Garantie):
„Kann diese Funktion etwas am System ändern?" — Wenn ja → STOPP,
gehört nicht in cci.

Cross-Repo-Lib-Trennung (DevOps-Direktive 2026-05-06): cci nutzt
KEINE Imports aus `ccc.system.*`. Eigene minimale Implementierung.
"""

from __future__ import annotations

import subprocess
from typing import Optional

# Whitelist: command-name -> erlaubte erste-Argumente (cmd[1])
# None = jedes erste-Argument erlaubt (Befehl ist inhärent read-only)
COMMAND_WHITELIST: dict[str, Optional[frozenset[str]]] = {
    # dpkg-query: purpose-built Read-Only-Tool (KEIN dpkg, weil dpkg
    # general-purpose mit -i/-r/-P-Mutation-Surface ist — Senior-Schärfung
    # AI039 SS2 2026-05-08: bei Read-Write- vs. Read-Only-Tool das
    # Read-Only-Tool bevorzugen, auch wenn Whitelist beide „sicher" macht).
    "dpkg-query": frozenset({
        "-l", "-W", "-s", "--list", "--show", "--status",
    }),
    # systemctl: nur Listing/Status/Cat (KEIN start/stop/restart/enable/disable)
    "systemctl": frozenset({
        "list-units", "list-unit-files", "list-machines", "list-jobs",
        "list-timers", "list-dependencies",
        "status", "is-active", "is-enabled", "is-failed",
        "cat", "show",
    }),
    # KEIN apt/apt-cache (Senior-Schaerfung AI039 SS5-Boundary 2026-05-08:
    # SS3.1-3.4 + SS4 + SS5 nutzen kein apt — Stdlib-Reflex hat dpkg-query
    # statt apt list, Path.read_text statt cat etc. Wenn kuenftiger SS
    # apt-Aufrufe braucht, mit konkreter Subkommando-Whitelist zurueckbringen.
    # Pattern-Anker: minimal-surface > nice-to-have-future.
    # pipx: nur list/--version/environment (KEIN install/upgrade/uninstall)
    "pipx": frozenset({
        "list", "--version", "-V", "environment", "--help", "-h",
    }),
    # php / node: nur Version-Detection (KEIN script-execution).
    # Senior-Schaerfung AI039 SS3.3 2026-05-08: konkrete Subkommando-
    # Whitelist (--version/-v), KEIN None-Fallback (defense-in-depth-
    # Pattern aus SS2 find/dpkg-Lehre).
    "php": frozenset({"--version", "-v"}),
    "node": frozenset({"--version", "-v"}),
    # Inhärent Read-Only — alle Argumente erlaubt.
    # KEIN cat (Senior-Schaerfung AI039 SS5-Boundary 2026-05-08: Path.read_text()
    # ist Stdlib-Idiomatik in apps/typo3.py, cat-Eintrag obsolet seit SS4).
    "uname": None,
    "ls": None,
    "stat": None,
    "readlink": None,
    # KEIN `find` als None-Fallback (Senior-Schärfung AI039 SS2 2026-05-08:
    # find ist „loaded gun"-Risiko via -delete/-exec, Phase 1 nutzt find
    # nicht. Wenn künftiger SS find braucht: mit konkreter Subkommando-
    # Whitelist `{-type, -name, -path, -maxdepth}` zurückbringen, NICHT
    # als None. Pattern-Anker: minimal-surface > nice-to-have-future).
}


class ReadOnlyViolationError(RuntimeError):
    """Erhoben wenn ein subprocess-Aufruf nicht in der Whitelist ist."""


def _validate_cmd(cmd: list[str]) -> None:
    """Prüft `cmd` gegen `COMMAND_WHITELIST`.

    Raises:
        ReadOnlyViolationError: bei leerer Liste, nicht-whitelisted Command,
            oder nicht-whitelisted Subkommando/Flag.
    """
    if not cmd:
        raise ReadOnlyViolationError("Empty command list")

    base = cmd[0]
    if base not in COMMAND_WHITELIST:
        raise ReadOnlyViolationError(
            f"Command not in read-only whitelist: {base!r} (cmd={cmd})"
        )

    allowed_subs = COMMAND_WHITELIST[base]
    if allowed_subs is None:
        # Befehl ist inhärent read-only, jedes Argument erlaubt
        return

    if len(cmd) < 2:
        raise ReadOnlyViolationError(
            f"Command {base!r} requires a subcommand from "
            f"{sorted(allowed_subs)} (got: {cmd})"
        )

    if cmd[1] not in allowed_subs:
        raise ReadOnlyViolationError(
            f"Subcommand {cmd[1]!r} not in read-only whitelist for {base!r}: "
            f"allowed = {sorted(allowed_subs)} (cmd={cmd})"
        )


def safe_run(
    cmd: list[str],
    *,
    timeout: float = 10.0,
    env: Optional[dict[str, str]] = None,
) -> subprocess.CompletedProcess[str]:
    """Read-Only-validated `subprocess.run`.

    Validiert `cmd` gegen `COMMAND_WHITELIST`. Erhebt
    `ReadOnlyViolationError` bei nicht-whitelisted Aufruf.

    Returnt `subprocess.CompletedProcess` mit text=True + capture_output=True.
    `check=False` (Caller entscheidet, ob non-zero exit als Fehler).

    Args:
        cmd: subprocess-Argument-Liste (cmd[0] = Befehlsname).
        timeout: Sekunden bis subprocess.TimeoutExpired (Default 10s).
        env: optionales Environment-Dict (None = Parent-Env erben).

    Returns:
        subprocess.CompletedProcess mit stdout/stderr als str.
    """
    _validate_cmd(cmd)
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )

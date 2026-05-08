"""Tests für cci.system.safe_run — Whitelist-Validierung + Read-Only-Garantie."""

from __future__ import annotations

import pytest

from cci.system.safe_run import (
    COMMAND_WHITELIST,
    ReadOnlyViolationError,
    _validate_cmd,
    safe_run,
)


# Case 1: empty cmd-list -> ReadOnlyViolationError
def test_empty_cmd_raises() -> None:
    with pytest.raises(ReadOnlyViolationError, match="Empty command"):
        _validate_cmd([])


# Case 2: nicht-whitelisted command -> ReadOnlyViolationError
def test_unknown_command_raises() -> None:
    with pytest.raises(ReadOnlyViolationError, match="not in read-only whitelist"):
        _validate_cmd(["rm", "-rf", "/"])


# Case 3: whitelisted command mit None-allowance (z.B. uname) -> kein Raise
def test_inherent_readonly_command_passes() -> None:
    # uname hat None-Whitelist (alle Args erlaubt)
    _validate_cmd(["uname", "-r"])
    _validate_cmd(["uname", "-a"])
    _validate_cmd(["ls", "-la"])
    _validate_cmd(["readlink", "-f", "/usr/local/bin/python"])


# Case 4: whitelisted command + erlaubtes Subkommando -> kein Raise
def test_subcommand_whitelist_hit_passes() -> None:
    _validate_cmd(["pipx", "list", "--short"])
    _validate_cmd(["pipx", "--version"])
    _validate_cmd(["dpkg-query", "-W", "-f=${Package}\\n"])
    _validate_cmd(["systemctl", "status", "nginx"])
    _validate_cmd(["systemctl", "is-active", "mysql"])


# Case 5: whitelisted command + nicht-whitelisted Subkommando -> Raise
def test_subcommand_whitelist_miss_raises() -> None:
    # pipx install ist Mutation -> verboten
    with pytest.raises(ReadOnlyViolationError, match="not in read-only whitelist for 'pipx'"):
        _validate_cmd(["pipx", "install", "xed-foo"])
    # systemctl restart ist Mutation -> verboten
    with pytest.raises(ReadOnlyViolationError, match="not in read-only whitelist for 'systemctl'"):
        _validate_cmd(["systemctl", "restart", "nginx"])
    # php exec arbiträrer scripts -> verboten (nur --version/-v erlaubt)
    with pytest.raises(ReadOnlyViolationError, match="not in read-only whitelist for 'php'"):
        _validate_cmd(["php", "evil-script.php"])


# Case 6: whitelisted command ohne Subkommando-Arg (wo erforderlich) -> Raise
def test_subcommand_required_but_missing_raises() -> None:
    with pytest.raises(ReadOnlyViolationError, match="requires a subcommand"):
        _validate_cmd(["pipx"])  # kein erstes-Arg


# Case 7: safe_run mit whitelisted cmd ruft subprocess auf
def test_safe_run_executes_whitelisted_cmd() -> None:
    # uname -r läuft auf jedem Linux, kein Mock nötig
    result = safe_run(["uname", "-r"])
    assert result.returncode == 0
    assert result.stdout.strip()  # nicht leer


# Case 8: safe_run mit non-whitelisted cmd raised vor subprocess
def test_safe_run_blocks_mutation_attempt() -> None:
    # rm würde Filesystem verändern wenn ausgeführt — _validate_cmd
    # blockiert vor subprocess.run
    with pytest.raises(ReadOnlyViolationError):
        safe_run(["rm", "-rf", "/tmp/fake-test-dir"])


# Case 9: COMMAND_WHITELIST enthält keine bekannten Mutation-Befehle
def test_whitelist_excludes_mutation_commands() -> None:
    """Defensive: stellt sicher dass keine Mutation-Top-Level-Commands
    versehentlich whitelisted sind."""
    forbidden = {
        # Filesystem-Mutation
        "rm", "rmdir", "mv", "cp", "chmod", "chown",
        # Process-Mutation
        "kill",
        # Disk/Storage-Mutation
        "dd", "mkfs", "fsck",
        # System-Lifecycle
        "shutdown", "reboot",
        # Senior-Schärfung AI039 SS2 2026-05-08:
        # find ist Loaded-Gun-Risiko via -delete/-exec
        "find",
        # dpkg ist general-purpose Read-Write (-i/-r/-P);
        # nur dpkg-query (purpose-built read-only) ist whitelisted
        "dpkg",
        # Senior-Schärfung AI039 SS5-Boundary 2026-05-08: ungenutzt in
        # Phase 1 (Stdlib-Reflex hat dpkg-query/Path.read_text statt apt/cat).
        # Wenn künftig benötigt: mit konkreter Subkommando-Whitelist zurück.
        "cat",
        "apt",
        "apt-cache",
    }
    for cmd in forbidden:
        assert cmd not in COMMAND_WHITELIST, (
            f"FATAL: {cmd!r} ist Mutation-Befehl, darf NICHT whitelisted sein"
        )


# Case 10: positive Probe — find/dpkg sind via safe_run() geblockt
def test_safe_run_blocks_find_and_dpkg_explicitly() -> None:
    """Positive Probe (Senior-Schärfung AI039 SS2): find + dpkg sind
    via safe_run() als unwhitelisted blockiert. Schützt gegen versehentliche
    Re-Adds in COMMAND_WHITELIST in künftigen SS-Sprints."""
    with pytest.raises(ReadOnlyViolationError, match="not in read-only whitelist"):
        safe_run(["find", "/tmp", "-name", "*.txt"])
    with pytest.raises(ReadOnlyViolationError, match="not in read-only whitelist"):
        safe_run(["dpkg", "-l"])

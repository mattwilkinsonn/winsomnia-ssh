"""winsomnia-ssh: keep Windows from sleeping during a WSL SSH session.

Invoke from a shell rc inside an SSH-into-WSL session. The process:
  1. Verifies `python.exe` and `winsomnia` are reachable on PATH.
  2. Walks the parent chain looking for sshd; exits cleanly if absent.
  3. Double-forks to detach from the launching shell.
  4. Periodically respawns `winsomnia` (which calls SetThreadExecutionState
     on Windows) until the sshd ancestor exits.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time

import psutil

__version__ = "0.2.0"

# `winsomnia <minutes>` keeps Windows awake for that many minutes, then dies.
# Respawn faster than the keep-awake window expires so there's always at
# least one live winsomnia process pinning the system.
KEEPAWAKE_MINUTES = 3
TICK_SECONDS = 120  # 1-minute overlap with the previous spawn


def main() -> None:
    args = _parse_args()
    # Default Python logging only emits WARNING+, so info messages stay silent
    # unless --verbose. Critical prereq failures always surface.
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if msg := _check_prerequisites():
        logging.critical(msg)
        sys.exit(1)

    sshd = _find_sshd_ancestor()
    if sshd is None:
        logging.info("not in an ssh session; exiting")
        return

    _detach()
    _keep_awake_loop(sshd)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("winsomnia-ssh")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="show verbose logging"
    )
    return parser.parse_args()


def _check_prerequisites() -> str | None:
    python_exe = shutil.which("python.exe")
    if python_exe is None:
        return (
            "python.exe is not in PATH.\n"
            "Install Python for Windows via the official installer "
            "(https://www.python.org/downloads/). "
            "DO NOT use the Microsoft Store version - it cannot be launched from WSL."
        )
    if "WindowsApps" in python_exe:
        return (
            f"python.exe at {python_exe} is the Microsoft Store stub, "
            "which cannot be launched from WSL. "
            "Install Python via the official installer instead."
        )
    if shutil.which("winsomnia") is None:
        return "winsomnia is not in PATH. Reinstall winsomnia-ssh."
    return None


def _find_sshd_ancestor() -> psutil.Process | None:
    for parent in psutil.Process().parents():
        try:
            if parent.name() == "sshd":
                return parent
        except psutil.NoSuchProcess:
            continue
    return None


def _detach() -> None:
    """Double-fork into the background; redirect std streams to /dev/null.

    Original parent returns from main() so the launching shell can continue.
    The grandchild has no controlling terminal (via setsid) and its standard
    streams point at /dev/null, so later writes don't EPIPE if the user's
    terminal closes.
    """
    if os.fork() > 0:
        os._exit(0)
    os.setsid()
    if os.fork() > 0:
        os._exit(0)

    sys.stdout.flush()
    sys.stderr.flush()
    devnull = os.open(os.devnull, os.O_RDWR)
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        os.dup2(devnull, stream.fileno())
    os.close(devnull)


def _keep_awake_loop(sshd: psutil.Process) -> None:
    logging.info(
        "winsomnia-ssh detached; pinning host awake while sshd %d is alive", sshd.pid
    )
    while True:
        try:
            if not sshd.is_running():
                return
        except psutil.NoSuchProcess:
            return

        _reap_zombies()
        _spawn_winsomnia(KEEPAWAKE_MINUTES)
        time.sleep(TICK_SECONDS)


def _spawn_winsomnia(timeout_minutes: int) -> None:
    subprocess.Popen(
        ["winsomnia", str(timeout_minutes), "-q"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _reap_zombies() -> None:
    while True:
        try:
            if os.waitpid(-1, os.WNOHANG) == (0, 0):
                return
        except ChildProcessError:
            return


if __name__ == "__main__":
    main()

"""Tests for winsomnia_ssh.

Covers the testable surface: prerequisite checks and sshd-ancestor lookup.
The detach + keep-awake loop are intentionally not unit-tested (process
forking and a long-running OS-level loop don't unit-test cleanly); they're
verified by manual end-to-end use.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import psutil

from winsomnia_ssh import winsomnia_ssh as mod


class TestCheckPrerequisites:
    def test_missing_python_exe(self):
        with patch.object(mod.shutil, "which", return_value=None):
            msg = mod._check_prerequisites()
        assert msg is not None
        assert "python.exe" in msg

    def test_windowsapps_python_rejected(self):
        store_path = "/mnt/c/Users/x/AppData/Local/Microsoft/WindowsApps/python.exe"
        with patch.object(
            mod.shutil,
            "which",
            side_effect=lambda name: store_path
            if name == "python.exe"
            else "/usr/local/bin/winsomnia",
        ):
            msg = mod._check_prerequisites()
        assert msg is not None
        assert "Microsoft Store" in msg

    def test_missing_winsomnia(self):
        with patch.object(
            mod.shutil,
            "which",
            side_effect=lambda name: "/mnt/c/Python314/python.exe"
            if name == "python.exe"
            else None,
        ):
            msg = mod._check_prerequisites()
        assert msg is not None
        assert "winsomnia" in msg

    def test_all_present(self):
        lookup = {
            "python.exe": "/mnt/c/Python314/python.exe",
            "winsomnia": "/usr/local/bin/winsomnia",
        }
        with patch.object(mod.shutil, "which", side_effect=lookup.__getitem__):
            assert mod._check_prerequisites() is None


class TestFindSshdAncestor:
    @staticmethod
    def _proc(name: str) -> SimpleNamespace:
        return SimpleNamespace(name=lambda n=name: n)

    def test_returns_sshd_when_present(self):
        zsh = self._proc("zsh")
        sshd = self._proc("sshd")
        with patch.object(
            mod.psutil, "Process", return_value=SimpleNamespace(parents=lambda: [zsh, sshd])
        ):
            assert mod._find_sshd_ancestor() is sshd

    def test_returns_none_when_absent(self):
        zsh = self._proc("zsh")
        bash = self._proc("bash")
        with patch.object(
            mod.psutil, "Process", return_value=SimpleNamespace(parents=lambda: [zsh, bash])
        ):
            assert mod._find_sshd_ancestor() is None

    def test_skips_dead_processes_in_chain(self):
        class DeadProc:
            def name(self):
                raise psutil.NoSuchProcess(pid=99)

        sshd = self._proc("sshd")
        with patch.object(
            mod.psutil,
            "Process",
            return_value=SimpleNamespace(parents=lambda: [DeadProc(), sshd]),
        ):
            assert mod._find_sshd_ancestor() is sshd

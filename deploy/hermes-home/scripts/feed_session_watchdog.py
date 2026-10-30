#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical Zero-Drift Forwarding Shim for feed_session_watchdog.py.

Directly invokes the canonical script in the git repo:
D:\\Taadaa\\tiktok-luot nuoi acc\\scripts\\feed_session_watchdog.py
using the production automation virtualenv with -B (no stale bytecode).
Eliminates 4-way parity drift: any change in git is immediately live.
"""
from __future__ import annotations

import os
import subprocess
import sys

if sys.platform == "win32":
    _orig_subp_run = subprocess.run
    def _silent_subp_run(*args, **kwargs):
        if "creationflags" not in kwargs:
            kwargs["creationflags"] = 0x08000000
        return _orig_subp_run(*args, **kwargs)
    subprocess.run = _silent_subp_run

PY = r"D:\Taadaa\python-envs\automation\Scripts\python.exe"
SCRIPT = r"D:\Taadaa\tiktok-luot nuoi acc\scripts\feed_session_watchdog.py"
WORKDIR = r"D:\Taadaa\tiktok-luot nuoi acc\scripts"


def main(*args, **kwargs):
    if not os.path.isfile(SCRIPT):
        sys.stderr.write(f"[SHIM ERROR] Canonical script not found: {SCRIPT}\n")
        sys.exit(1)
    cmd = [PY, "-B", SCRIPT]
    if kwargs.get("mode"):
        cmd.append(f"--mode={kwargs['mode']}")
    cmd.extend(sys.argv[1:])
    proc = subprocess.run(cmd, cwd=WORKDIR)
    if __name__ == "__main__":
        sys.exit(proc.returncode)
    return proc.returncode


if __name__ == "__main__":
    main()

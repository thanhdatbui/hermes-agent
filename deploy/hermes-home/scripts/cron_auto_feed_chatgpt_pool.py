#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical Zero-Drift Forwarding Shim for cron_auto_feed_chatgpt_pool.py."""
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

PY = sys.executable
SCRIPT = r"D:\Taadaa\GPM auto\scripts\cron_auto_feed_chatgpt_pool.py"
WORKDIR = r"D:\Taadaa\GPM auto\scripts"

if not os.path.isfile(SCRIPT):
    sys.stderr.write(f"[SHIM ERROR] Script not found: {SCRIPT}\n")
    sys.exit(1)

proc = subprocess.run([PY, "-B", SCRIPT] + sys.argv[1:], cwd=WORKDIR)
sys.exit(proc.returncode)

"""Hermes Cron Launcher for Night Chain Pipeline (Reg Gmail -> Reg TikTok)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_SCRIPT = Path(r"D:\Taadaa\Tiktok_Reg\scripts\run_night_chain_pipeline.py")
PYTHON_EXE = r"D:\Taadaa\python-envs\automation\Scripts\python.exe"
if not Path(PYTHON_EXE).exists():
    PYTHON_EXE = sys.executable

def main() -> int:
    if not REPO_SCRIPT.exists():
        sys.stderr.write(f"Error: Not found {REPO_SCRIPT}\n")
        return 1
        
    cmd = [PYTHON_EXE, "-u", str(REPO_SCRIPT)]
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10800, # 3 tiếng
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.stdout:
        sys.stdout.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    return completed.returncode

if __name__ == "__main__":
    raise SystemExit(main())

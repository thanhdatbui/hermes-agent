"""Reap dead-owner device locks — Hermes cron no_agent wrapper.

Runs the canonical reap script with the automation python.  Non-zero exit or
traceback is surfaced by the cron runner; empty stdout stays silent.
"""
import subprocess
import sys

PY = r"D:\Taadaa\python-envs\automation\Scripts\python.exe"
SCRIPT = r"D:\Taadaa\tiktok-luot nuoi acc\scripts\reap-dead-owner-locks.py"

proc = subprocess.run(
    [PY, "-B", SCRIPT],
    capture_output=True,
    text=True,
    timeout=120,
    cwd=r"D:\Taadaa\tiktok-luot nuoi acc",
)
out = (proc.stdout or "").strip()
err = (proc.stderr or "").strip()
if proc.returncode == 0 and out:
    print(out)
elif proc.returncode == 0:
    sys.stderr.write("(no dead-owner locks)\n")
else:
    sys.stderr.write(err or f"exit code {proc.returncode}")
    sys.exit(proc.returncode if proc.returncode else 1)
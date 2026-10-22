"""
hermes_cron_silent_ps_wrapper.py
---------------------------------
Template: Hermes cron wrapper that spawns a PowerShell script
COMPLETELY silently (no CMD/PowerShell window ever appears on screen).

Required: both CREATE_NO_WINDOW flag AND -WindowStyle Hidden flag.
Either alone is insufficient — both are needed.

Usage:
  1. Copy this file, set PS_SCRIPT to your target .ps1 path.
  2. Place in D:\Taadaa\tools\<your_script_name>.py
  3. cp it to $LOCALAPPDATA/hermes/scripts/<your_script_name>.py
  4. cronjob(action='update', job_id='...', script='<your_script_name>.py')

Silence contract:
  - No output at all  → cron scheduler stays silent (watchdog pattern)
  - Print something   → cron delivers it to the configured destination
  - sys.exit(non-zero)→ cron logs an error alert
"""

import subprocess
import sys
import os

PS_SCRIPT = r"D:\Taadaa\CHANGE_ME\your_script.ps1"

# Both flags required. CREATE_NO_WINDOW alone still shows a flash on some
# Windows builds. -WindowStyle Hidden alone doesn't suppress conhost creation.
CREATE_NO_WINDOW = 0x08000000


def main():
    if not os.path.exists(PS_SCRIPT):
        print(f"SYNC_ERROR: script not found: {PS_SCRIPT}", flush=True)
        sys.exit(1)

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-WindowStyle", "Hidden",
            "-File", PS_SCRIPT,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0:
        print(f"ERROR: exit={result.returncode}", flush=True)
        if stdout:
            print(stdout, flush=True)
        if stderr:
            print(stderr, flush=True)
        sys.exit(result.returncode)

    # Only print when there is meaningful output (skip "no change" markers)
    # Adjust the NO_CHANGE_MARKER to match your script's silent-success output
    NO_CHANGE_MARKER = "UNCHANGED"
    if stdout and NO_CHANGE_MARKER not in stdout:
        print(stdout, flush=True)
    # Stay completely silent when nothing changed


if __name__ == "__main__":
    main()

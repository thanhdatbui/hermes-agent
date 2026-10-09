# Dual-Tier Reboot Survival & Daemon Watchdog Pattern

## Context & Problem
In automated farm controller & worker hosts (such as Windows machines running 24/7 video processing, downloading, or phone automation):
1. **Scheduled or spontaneous reboots:** Machines reboot on schedule (e.g. 04:45 AM farm reboot) or crash recovery.
2. **Crash & silent freeze vulnerability:** Network disconnects, proxy timeouts, or SQLite WAL disk I/O locks (`OperationalError: disk I/O error`) can crash long-running worker loops mid-day without rebooting the machine.
3. **Flashing console / task scheduler blocks:** Direct Task Scheduler CLI creation often encounters permission or execution timeout blocks, while `.bat` launchers in startup flash console windows and disrupt gaming or interactive usage.

## Solution Architecture: The 2-Tier Defense + Kernel Lock

### Tier 1: Windows User Logon Auto-Start (Reboot Survival)
Target: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\<launcher>.vbs`
Pre-requisite: `AutoAdminLogon = 1` in `HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon`.

```vbscript
' C:\Users\<User>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\start_service_watchdog.vbs
Option Explicit
Dim WshShell
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """C:\Path\To\python.exe"" ""C:\Users\<User>\watchdog_service.py""", 0, False
Set WshShell = Nothing
```
*Note:* The `0, False` parameters ensure zero console flicker (`SW_HIDE`) and non-blocking execution.

### Tier 2: Hermes Cron Periodic Watchdog (Mid-Run Crash Recovery)
Target: Hermes local cronjob configured in `jobs.json` (`schedule: "*/15 * * * *"` with `deliver: "local"`, `no_agent: true`).
Script: `watchdog_service.py` under `~/.hermes/scripts/`.

The watchdog checks process existence via `psutil`:
```python
# watchdog_service.py
import sys, subprocess, psutil

def is_running():
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = " ".join(p.info.get('cmdline') or [])
            if "target_worker_script.py" in cmd:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def main():
    if is_running():
        return 0

    # Spawn detached daemon process
    python_exe = r"C:/Path/To/python.exe"
    script_p = r"C:/Path/To/target_worker_script.py"
    subprocess.Popen(
        [python_exe, "-u", script_p],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    )
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Concurrency Protection: Non-Blocking Kernel File Lock
Because Tier 1 (on reboot) and Tier 2 (every 15m) can potentially fire near each other, the worker daemon MUST protect itself with a non-blocking kernel lock (`msvcrt` on Windows) so only one daemon ever runs:

```python
import sys, os, msvcrt

LOCK_FILE = r"C:/Users/<User>/AppData/Local/hermes/locks/service_name.lock"

def acquire_lock():
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    try:
        f = open(LOCK_FILE, "w")
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        return f
    except (IOError, OSError):
        return None

def main():
    lock_fd = acquire_lock()
    if not lock_fd:
        print("[LOCK] Another service instance is already running. Exiting cleanly.")
        sys.exit(0)
    
    # Run service loop...
```

## Verification Checklist
1. `Test-Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\<launcher>.vbs"` returns `True`.
2. `python -c "import json; ..."` verifies job in `jobs.json` is `enabled: true`.
3. Simulating crash (`taskkill /F /PID <pid>`) results in the cron watchdog restoring the process within 15 minutes.
4. Reboot test results in immediate service restoration without console popups.

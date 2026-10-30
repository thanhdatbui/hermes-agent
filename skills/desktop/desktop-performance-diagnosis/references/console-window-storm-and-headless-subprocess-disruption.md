# Windows Desktop Flashing / Console Window Storms from Headless Automation

## Symptom Profile
- User experiences rapid screen flashing / flickering ("nháy nháy liên tục").
- Fleeting console windows (black borders or CMD titlebars like `adb.exe`, `ffmpeg.exe`, `curl.exe`) appear and instantly vanish across the desktop.
- Often coincides with scheduled background jobs, cron tasks, or farm maintenance batches launching worker pools.

## Diagnostic Fast-Path (PowerShell O(1))
Run a parent-child relationship query to find the launcher process tree:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'adb|cmd|powershell|python' } | Select-Object ProcessId, ParentProcessId, Name, CommandLine | Format-Table -AutoSize
```

Trace `ParentProcessId` backwards:
1. Short-lived console child (e.g. `adb.exe`).
2. Parent worker process (e.g. `pythonw.exe clear-tiktok-cache.py`).
3. Root orchestrator / scheduler (e.g. `pythonw.exe cron_clear_tiktok_cache.py` or Hermes Gateway).

## Root Cause
- Console subsystem binaries (`IMAGE_SUBSYSTEM_WINDOWS_CUI`) spawned from headless/GUI parents (`pythonw.exe`, Windows Services, task schedulers) default to allocating a new console window if one is not already attached.
- In multi-threaded worker pools (e.g., 20+ workers iterating over 70+ devices), hundreds of subcommands execute per minute, resulting in an aggressive "console window storm".
- **Misconception:** `pythonw.exe` hides the Python interpreter itself, but does NOT automatically suppress console windows of child processes spawned via `subprocess.run()` or `Popen()`.

## Standard Prevention & Fix
Always supply `creationflags=subprocess.CREATE_NO_WINDOW` on Windows:

```python
import os
import subprocess
from typing import Any

def get_subprocess_window_kwargs() -> dict[str, Any]:
    if os.name != "nt":
        return {}
    return {"creationflags": subprocess.CREATE_NO_WINDOW}

# Usage:
subprocess.run(cmd, capture_output=True, text=True, timeout=10, **get_subprocess_window_kwargs())
```

### PowerShell Pitfall: `Start-Process -WindowStyle Hidden` Still Flashes Windows
- **Flawed approach:** `Start-Process -FilePath "cmd.exe" -ArgumentList $cmd -PassThru -WindowStyle Hidden`
- **Why it fails:** PowerShell creates the Win32 console window normally on desktop session 1, then asynchronously sends `ShowWindow(SW_HIDE)` ~50ms later. In DirectX exclusive fullscreen games (War3, TFT), this 50ms window steals visual focus, resets graphics adapter exclusive mode, and causes an instant black screen flash / flicker.
- **Robust Win32 API Fix:**
```powershell
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "cmd.exe" # or python.exe
$psi.Arguments = $cmd
$psi.CreateNoWindow = $true
$psi.UseShellExecute = $false
$p = [System.Diagnostics.Process]::Start($psi)
```

### Multi-Runtime `sitecustomize.py` Coverage Pitfall
When using `sitecustomize.py` to transparently force `CREATE_NO_WINDOW` across all Python `subprocess.Popen` / `subprocess.run` calls:
- Inspect **ALL** installed Python versions and virtualenvs on the host (e.g. `Python311`, `Python312`, project venvs).
- If one runtime is missed (e.g. `Python312` while only `Python311` was patched), scripts targeting `Python312` will bypass the hook and flash unsuppressed console windows during execution.
- Always audit `sitecustomize.py` presence across all directories under `C:\Users\<User>\AppData\Local\Programs\Python\Python*` and project runtime folders.

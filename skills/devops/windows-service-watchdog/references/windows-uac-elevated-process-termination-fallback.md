# Windows UAC Elevated Process Termination Fallback in Watchdogs

## Problem Context & Symptoms
In Windows environments (such as phone farms, emulator hosts, or screen mirroring stations), certain desktop applications (e.g. `xiaowei.exe`, Total Control, Android screen mirrors, USB hub tools) run with **UAC Elevation** (Run as Administrator / High Integrity Level) to access raw USB drivers, display APIs, or global hotkeys.

Meanwhile, background watchdogs, scheduled tasks, and autonomous agent loops (such as Hermes cron jobs) typically execute in the standard interactive user context with a **Medium Integrity Level** (`is_admin: False`).

### Symptoms
When the watchdog detects that the application has been idle, hung, or needs to be terminated:
1. `taskkill /F /IM target.exe` fails with:
   ```text
   ERROR: The process "target.exe" with PID <PID> could not be terminated.
   Reason: Access is denied.
   ```
2. PowerShell `Stop-Process -Id <PID> -Force` fails with:
   ```text
   Stop-Process : Cannot stop process "target (<PID>)" because of the following error: Access is denied
   ```
3. Win32 API `PostMessage(hwnd, WM_CLOSE, 0, 0)` fails with `GetLastError() == 5` because **UIPI (User Interface Privilege Isolation)** blocks window messages from lower-integrity to higher-integrity processes.
4. The watchdog loop repeatedly triggers every tick (e.g. every 5 minutes), reports failure or stays stuck, and the target application remains open indefinitely, hogging USB bandwidth, CPU, and RAM.

---

## Root Cause
Under the Windows Security Model (User Account Control):
- A process running at Medium Integrity cannot acquire `PROCESS_TERMINATE` access rights via `OpenProcess()` on a process running at High Integrity (Administrator), even if both processes belong to the exact same Windows user account (`DESKTOP-XXX\User`).
- Native Win32 `TerminateProcess` and commands wrapping it (`taskkill.exe`, `Stop-Process`) require `PROCESS_TERMINATE` rights on the process handle.

---

## Solution: WMI / CIM Process Terminate Fallback
The Windows Management Instrumentation (WMI / CIM) infrastructure runs via the WMI service (`winmgmt`). When invoked within the user's interactive session, the WMI method `Win32_Process.Terminate` can terminate the process in the user's session without requiring the calling script to hold elevated privileges.

### PowerShell CIM Command
```powershell
Get-CimInstance Win32_Process -Filter "Name = 'target.exe'" | Invoke-CimMethod -MethodName Terminate
```
Or targeting a specific PID:
```powershell
Get-CimInstance Win32_Process -Filter "ProcessId = $targetPid" | Invoke-CimMethod -MethodName Terminate
```

Performance: ~0.5s execution time, returns `ReturnValue: 0` on success.

---

## Python Watchdog Implementation Pattern
Always use a resilient dual-tier termination strategy:
1. **Tier 1 (Fast path):** Try `taskkill.exe /F /IM <name>`. If exit code is 0 and process is no longer running, return `True`.
2. **Tier 2 (Elevated fallback):** If `taskkill` fails or is denied access, invoke the PowerShell CIM `Win32_Process.Terminate` method.
3. **Verification:** Confirm process disappearance via process lookup before declaring success.

```python
import subprocess

def is_process_running(process_name: str) -> bool:
    try:
        r = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return process_name.lower() in r.stdout.lower()
    except Exception:
        return False

def force_close_process(process_name: str) -> bool:
    """Đóng process an toàn với cơ chế fallback qua WMI/CIM khi process chạy quyền Administrator."""
    try:
        # Tier 1: Fast path với taskkill
        r = subprocess.run(
            ["taskkill", "/F", "/IM", process_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if (r.returncode == 0 or "success" in r.stdout.lower()) and not is_process_running(process_name):
            return True

        # Tier 2: Fallback qua WMI/CIM nếu taskkill bị Access Denied
        ps_cmd = f'Get-CimInstance Win32_Process -Filter "Name = \'{process_name}\'" | Invoke-CimMethod -MethodName Terminate'
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            timeout=8,
        )
        return not is_process_running(process_name)
    except Exception as e:
        return False
```

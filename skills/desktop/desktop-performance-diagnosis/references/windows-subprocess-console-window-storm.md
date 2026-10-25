# Windows Subprocess Console Window Storm (Flashing Command Prompt Windows)

## Symptom
The user observes a rapid-fire cascade of Command Prompt (`cmd.exe`) windows opening and closing in fractions of a second across the desktop, displaying titles like:
`C:\Program Files (x86)\xiaowei\tools\adb.exe` (or `adb.exe`, `python.exe`, `curl.exe`).
This causes noticeable desktop stutter, visual flicker, and window focus jitter.

## Root Cause
1. **Windows Subsystem Behavior with `pythonw.exe` / Background Daemons**:
   - Background tasks, cron jobs, and daemons launched via `pythonw.exe` or headless launchers run without an attached console.
   - When a Python script invokes a console subsystem executable via `subprocess.run()` or `subprocess.Popen()` on Windows without passing `creationflags=subprocess.CREATE_NO_WINDOW` (`0x08000000`), Windows automatically allocates a visible console window for the child process.
2. **Amplification by Multi-worker Concurrency**:
   - Single periodic calls may flash briefly, but multi-worker automation (e.g. 20-30 threads clearing cache, polling devices, or pinging WiFi) executing sequences of commands produce 30-50+ transient windows per second.

## Required Resolution

### Pattern 1: Helper Wrapper (Recommended for scripts with multiple subprocess calls)
```python
import os
import subprocess

def subp_run(*args, **kwargs):
    if os.name == "nt" and "creationflags" not in kwargs:
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(*args, **kwargs)
```
Replace all `subprocess.run(...)` calls with `subp_run(...)`.

### Pattern 2: Global Keyword Arguments
```python
import os
import subprocess

WIN_KWARGS = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}

subprocess.run([ADB, "-s", serial, "shell", ...], capture_output=True, timeout=10, **WIN_KWARGS)
```

### Pattern 3: Module-Level Subprocess Monkeypatch (Preferred for zero-touch refactoring)
When refactoring legacy monolith or watchdog scripts with multiple internal functions without altering dozens of call sites:
```python
import sys
import subprocess

if sys.platform == "win32":
    _orig_subp_run = subprocess.run
    def _silent_subp_run(*args, **kwargs):
        if "creationflags" not in kwargs:
            kwargs["creationflags"] = 0x08000000
        return _orig_subp_run(*args, **kwargs)
    subprocess.run = _silent_subp_run
```

### Pattern 4: Global Environment Hardening via `sitecustomize.py`
To eliminate console window flashes across all sub-scripts and Python environments permanently:
```python
# In site-packages/sitecustomize.py
import sys
if sys.platform == "win32":
    try:
        import subprocess
        if not getattr(subprocess, "_hermes_no_window_patched", False):
            subprocess._hermes_no_window_patched = True
            _orig_popen_init = subprocess.Popen.__init__
            def _silent_popen_init(self, *args, **kwargs):
                flags = kwargs.get("creationflags", 0)
                kwargs["creationflags"] = (flags & ~0x00000008) | 0x08000000
                _orig_popen_init(self, *args, **kwargs)
            subprocess.Popen.__init__ = _silent_popen_init

            _orig_run = subprocess.run
            def _silent_run(*args, **kwargs):
                flags = kwargs.get("creationflags", 0)
                kwargs["creationflags"] = (flags & ~0x00000008) | 0x08000000
                return _orig_run(*args, **kwargs)
            subprocess.run = _silent_run
    except Exception:
        pass
```

**Verification Pattern over Windows OpenSSH (PowerShell EncodedCommand):**
To verify remote venv patch status without cmd.exe argument/quote stripping:
```python
import base64, subprocess
ps_code = """
$p = & 'D:\\Taadaa\\python-envs\\automation\\Scripts\\python.exe' -c "import subprocess; print('PATCHED:', getattr(subprocess, '_hermes_no_window_patched', False))"
Write-Output $p
"""
b64 = base64.b64encode(ps_code.encode("utf-16le")).decode("ascii")
cmd = ["ssh", "-o", "BatchMode=yes", "admin-farm", f"powershell -NoProfile -NonInteractive -EncodedCommand {b64}"]
res = subprocess.run(cmd, capture_output=True, text=True)
# Expected: PATCHED: True
```

**CRITICAL VIRTUALENV PITFALL:**
A `sitecustomize.py` placed inside system Python (`AppData\Local\Programs\Python\Python3xx\Lib\site-packages`) will **NOT** be executed by virtual environments (e.g. `python-envs\automation\Lib\site-packages`). Virtual environments have isolated site directories.
When batch runners (like `run-feed-session.ps1` launching 25-40 workers) use a venv Python binary, you **MUST copy `sitecustomize.py` directly into each active virtualenv's `Lib\site-packages`**. Otherwise, fleet workers will continue executing unsuppressed console binaries (`adb.exe`), maintaining the console window storm even when base Python appears patched.

## Hidden Scheduled Task & WindowStyle Hidden Pitfall
Even when background scheduled tasks (e.g. `Hermes_Gateway_Watchdog`, `WakeUpForCron`) use `wscript.exe` or `powershell.exe -WindowStyle Hidden` or `cmd.exe /c exit`, running on short intervals (e.g. every 2 minutes `PT2M`) causes Windows Desktop Window Manager (DWM) to allocate a transient console session. In fullscreen/borderless games (Warcraft 3, League of Legends), this creates an intermittent 1-frame screen blink/flicker ("lâu lâu nháy màn hình 1 cái").
- **Diagnosis:** Query PowerShell Event Log ID 400 (`HostApplication`) to trace recurring hidden PowerShell invocations.
- **Fix:** Disable or consolidate redundant watchdog scheduled tasks in favor of persistent daemons or event-driven triggers.

## Coordinator Subagent Dispatch Rule
When patching multiple standalone scripts across directories to address console storms:
- Do not bundle 4+ scripts into one worker dispatch prompt (causes 600s timeout / iteration exhaustion).
- Decompose into 1-2 scripts per worker with exact `old_string` -> `new_string` replacement contracts and focused syntax checks (`python -m py_compile <path>`).

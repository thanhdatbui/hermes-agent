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

## Coordinator Subagent Dispatch Rule
When patching multiple standalone scripts across directories to address console storms:
- Do not bundle 4+ scripts into one worker dispatch prompt (causes 600s timeout / iteration exhaustion).
- Decompose into 1-2 scripts per worker with exact `old_string` -> `new_string` replacement contracts and focused syntax checks (`python -m py_compile <path>`).

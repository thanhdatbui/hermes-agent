# Multi-Runtime Sitecustomize Gap & PowerShell ProcessStartInfo Anti-Flicker

## 1. Problem Description
On Windows desktop machines where interactive games (such as Warcraft III `w3l.exe` / `war3.exe` or Teamfight Tactics `tftclient.exe`) run in Session 1, screen flickering / momentary black screens / micro-stutters occur whenever:
1. A PowerShell script invokes background jobs using `Start-Process -FilePath "cmd.exe" -ArgumentList ... -WindowStyle Hidden`.
2. Python sub-runtimes or virtualenvs lack `sitecustomize.py` monkey-patching `subprocess.Popen` / `subprocess.run` with `CREATE_NO_WINDOW (0x08000000)`.

## 2. Root Cause Analysis
- **PowerShell WindowStyle Hidden Flaw:**
  Windows kernel always instantiates a Win32 Console Window before PowerShell can issue `ShowWindow(SW_HIDE)`. During the initial ~50ms frame, the console window steals DirectX exclusive focus, resulting in visual tearing or black frame flickers.
- **Multiple Python Environments on Admin/Worker Hosts:**
  Deploying anti-flicker hooks only to `Python311` or a single virtualenv leaves other installed runtimes (`Python312`, secondary venvs) unpatched. Any script executed with an unpatched runtime will spawn child processes (e.g. `adb.exe`, `tasklist.exe`) with default creation flags, re-introducing console window flashes.

## 3. Remediation Standards
### A. Pure PowerShell Invocations
Never use `Start-Process cmd.exe -WindowStyle Hidden`. Always configure `System.Diagnostics.ProcessStartInfo`:
```powershell
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "cmd.exe"
$psi.Arguments = $cmd
$psi.CreateNoWindow = $true
$psi.UseShellExecute = $false
$p = [System.Diagnostics.Process]::Start($psi)
```

### B. Fleet-wide Python Sitecustomize Coverage
Every Python installation and virtualenv site-packages directory must contain `sitecustomize.py` forcing `CREATE_NO_WINDOW`:
```python
import sys, subprocess

if sys.platform == "win32":
    try:
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
Ensure deployment targets cover all active runtimes (`Python311`, `Python312`, `D:\Taadaa\python-envs\*`, and all `D:\CodexRuntime\*\venv`).

# Remote SSH PowerShell Screen Flicker & Overlay Conflict Prevention

## Symptom
While a user is actively playing a DirectX/OpenGL fullscreen or borderless game (such as Warcraft III `War3.exe`, League of Legends, or TFT) on a Windows remote host (e.g. `admin-farm`), the screen suffers rapid or intermittent flickering/flashing ("cứ chớp chớp trên màn hình", "nháy nháy liên tục") and mouse focus drops.

## Root Causes Discovered

1. **Remote SSH Invocation of PowerShell Lacking `-WindowStyle Hidden`**:
   - Background fleet runners (e.g. `run_tiktok.py` / `multi_machine_feed_session.py` upload hooks) spawn commands across SSH:
     `ssh admin-farm 'powershell -NoProfile -NonInteractive -Command ...'`
   - **OpenSSH Server Subsystem Trap**: On Windows, OpenSSH executes commands through `cmd.exe /c powershell...`. Even when Python on the remote machine is protected by `sitecustomize.py`, the outer `powershell.exe` process itself is invoked without `-WindowStyle Hidden`. Windows OpenSSH Server allocates a dedicated `conhost.exe` console session for every remote invocation.
   - When 20-35 parallel fleet workers run upload hooks simultaneously, up to 35 active `conhost.exe` and `powershell.exe` instances appear and disappear in the background. Windows Desktop Window Manager (DWM) constantly detects new console surfaces, triggering composite screen flickers and frame-time hitches in fullscreen games.

2. **Stale `cua-driver` Full-Screen Topmost Transparent Overlay**:
   - When `cua-driver` runs in interactive Session 1, it maintains an invisible 1920x1080 transparent click overlay (`Cua.AgentCursorOverlay.default`).
   - Under normal desktop use, the overlay is unnoticeable. However, when background processes churn or conhost contexts allocate, DWM struggles to composite DirectX swapchains beneath the topmost transparent window, turning minor background process churn into violent, persistent screen flickering.

3. **Desktop Shell Change Storms (`SHChangeNotify`)**:
   - Scripted batch writes to `%USERPROFILE%\Desktop` (e.g. copying 20+ `.lnk` files in rapid succession to restore missing shortcuts) trigger a flood of shell redraw events. Windows Explorer repeatedly repaints the composite desktop surface behind or over the active game.

4. **State-Blind Transfer Watchdogs**:
   - A cron watchdog configured to trigger payload transfers based purely on disk space (e.g. `D_FREE >= 52 GB`) without verifying whether the target payload (e.g. `D:\Riot Games\...`) already exists will fire on every interval, spinning up hung socket connections, SSH processes, and disk I/O.

5. **PowerShell `Start-Process cmd.exe -WindowStyle Hidden` Transient Console Pop-Up**:
   - In local and remote PowerShell orchestration scripts (e.g. `run_parallel.ps1` for batch phone-farm tasks), spawning workers via:
     `Start-Process -FilePath "cmd.exe" -ArgumentList $cmd -PassThru -WindowStyle Hidden`
     is a major trap.
   - **Win32 Window Allocation Timing**: On Windows, `Start-Process ... -WindowStyle Hidden` does NOT prevent the console window from being created. Win32 kernel first allocates the console window surface on the active desktop, and only then does PowerShell send `ShowWindow(SW_HIDE)`.
   - The ~50ms window exposure appears as an instantaneous black flash that steals focus. In exclusive fullscreen or borderless DirectX games (Warcraft III `w3l.exe`/`War3.exe`, TFT), this 1-frame focus drop causes the graphics driver to cycle exclusive mode, resulting in violent screen blinking / flickering ("chớp màn hình", "nháy nháy liên tục").
   - **Distinction from Silent Downloaders**: Never falsely diagnose background compute or download workers (e.g. `download_by_niche.py`) as the cause of visual screen blinking if they execute under `pythonw.exe` with `CREATE_NO_WINDOW`. As the user noted ("downloader có ảnh hưởng game đâu?"), background I/O causes bandwidth/disk usage, but CANNOT generate console surface pop-ups. Always target console subsystem allocations and focus stealers.

---

## Mechanical Resolution & Guard Patterns

### 1. Zero-Flicker Subprocess Spawning in PowerShell
Never use `Start-Process cmd.exe -WindowStyle Hidden`. Use .NET `ProcessStartInfo` with `CreateNoWindow = $true` and `UseShellExecute = $false` to ensure the console surface is never allocated:

```powershell
# In run_parallel.ps1 or any PowerShell worker dispatcher:
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $pythonExe
$psi.Arguments = "worker_script.py $M $extraArgs"
$psi.CreateNoWindow = $true
$psi.UseShellExecute = $false
$p = [System.Diagnostics.Process]::Start($psi)
```
Or when shell redirection is strictly needed, point `FileName` to `cmd.exe` but still enforce `CreateNoWindow = $true`:
```powershell
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "cmd.exe"
$psi.Arguments = "/c chcp 65001 >nul 2>&1 && set PYTHONIOENCODING=utf-8 && `"$pythonExe`" worker.py $M > `"$logFile`" 2>&1"
$psi.CreateNoWindow = $true
$psi.UseShellExecute = $false
$p = [System.Diagnostics.Process]::Start($psi)
```

### 1. Enforce `-WindowStyle Hidden` on Remote SSH Dispatch
In fleet runners and upload dispatchers, always supply `-WindowStyle Hidden` and `creationflags=subprocess.CREATE_NO_WINDOW`:

```python
# In multi_machine_feed_session.py or any remote runner
command = [
    "ssh",
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=10",
    "-o", "ServerAliveInterval=15",
    "-o", "ServerAliveCountMax=3",
    admin_ssh_target,
    f'powershell -NoProfile -NonInteractive -WindowStyle Hidden -Command "{remote_cmd}"',
]
subp_kwargs = {
    "capture_output": True,
    "text": True,
    "timeout": subprocess_timeout,
    "cwd": str(tiktok_repo),
}
if sys.platform == "win32":
    subp_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
proc = subprocess.run(command, **subp_kwargs)
```

### 2. AST & Segment Hook Enforcement (`guard_cronjob_safety.py`)
Never rely on verbal discipline promises ("từ nay sẽ tuân thủ..."). Enforce the constraint mechanically in the pre-tool-use guard:
- **AST Inspector (`scan_script`)**: Walk `ast.Call` nodes for `subprocess.run/Popen`. If the command contains `ssh` / `admin-farm` / `admin_ssh` and invokes `powershell` or `pwsh`, check for `-w(?:indowstyle)?\s+hidden`. Block fail-closed with `CONSOLE_WINDOW_BLOCKED` if missing.
- **Segment Inspector (`check_segment`)**: For terminal commands and cron scripts, verify that any segment invoking SSH to `admin-farm` with `powershell` contains `-WindowStyle Hidden`.

### 3. O(1) Instant Relief for Gaming Sessions
- **Kill Stale Overlays**: Run `Stop-Process -Name cua-driver -Force` via SSH on the target machine.
- **Pause Redundant Transfer Watchdogs**: When target files are intact, immediately pause the recurring cron watchdog via `cronjob(action='pause', job_id=...)`.
- **Verify Session Id of Console Processes**: Ensure no `cmd.exe` or `powershell.exe` instances are running in interactive Session 1 (`Get-Process -IncludeUserName | Where-Object { $_.SessionId -eq 1 }`).

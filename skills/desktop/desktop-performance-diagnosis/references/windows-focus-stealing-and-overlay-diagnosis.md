# Windows Focus Stealing & Fullscreen Overlay Diagnosis

## Symptom

User reports an application, desktop, or game repeatedly losing focus, stuttering, minimizing, or having the screen hijacked ("cứ chiếm màn hình hoài", "mất chuột", "tự nhảy ra ngoài").

## Common Culprits on Workstations / Automation Hosts

1. **Game Overlays (Overwolf, MetaTFT, Discord, GeForce Experience):**
   - Overwolf/MetaTFT spawns multiple CEF/Electron overlay windows, including full-screen windows (e.g. `1936x1056` at `(-8, -8)`) that intermittently seize `GetForegroundWindow` from borderless/fullscreen games.
2. **Automated Multi-Profile Browsers (GPMLogin, AdsPower, Multilogin):**
   - Automation supervisors running on intervals (e.g. every 5–15 min) launch or restore browser profiles. Even if spawned off-screen or minimized, navigation and modal prompts trigger Windows shell focus events or taskbar flashing.
3. **Ghost Overlay Drivers & Utilities (e.g. Cua-Driver, Touch/Pen Overlays):**
   - Transparent fullscreen click-through windows (`WS_EX_TOPMOST` or `Cua.AgentCursorOverlay.default` at `1920x1080`).
4. **Hanging Helper Processes (`Not Responding`):**
   - Stalled companion processes (e.g. `TFTAcademy.exe`, `OverwolfBrowser.exe`) consuming CPU or stuck in OleMainThreadWndName message loops.
5. **High-Concurrency Fleet Runners Missing Headless Flags (PowerShell `-WindowStyle Hidden` & Subprocess `CREATE_NO_WINDOW`):**
   - Background runners (e.g. `run-feed-session.ps1` or multi-device ADB loops) launched via PowerShell without `-WindowStyle Hidden` allocate a visible or focus-grabbing console window.
   - When scripts spawn hundreds of CLI subprocesses (e.g. `adb.exe shell dumpsys ...`, `omp.cmd`, `cmd.exe`) without `creationflags=subprocess.CREATE_NO_WINDOW` (`0x08000000`), Windows constantly spawns and destroys `conhost.exe` instances, causing rapid micro-flickers, DWM composite hiccups, and focus stealing from fullscreen DirectX games (TFT, LoL, War3).

## Diagnostic Protocol

### 1. Rapid Process & Window Title Scan (Avoid `tasklist /v` Hangs)

`tasklist /v /fo csv` enumerates every thread and window title across all system processes, which easily times out (>30s) on hosts with 100+ processes.
Instead, use filtered queries:

```bash
# Filtered window inspection for suspected suites (instant)
tasklist /fi "IMAGENAME eq Overwolf.exe" /v
tasklist /fi "IMAGENAME eq GPMLogin.exe" /v
tasklist /fi "IMAGENAME eq TFTAcademy.exe" /v
tasklist /fi "IMAGENAME eq chrome.exe" /v
```

### 2. Live Foreground Window Sampling (Catch the Focus Thief in Real-Time)

Sample `GetForegroundWindow` over a 5–10 second window to catch intermittent focus hijacking:

```python
import ctypes
import time
import psutil

user32 = ctypes.windll.user32
print("Sampling foreground window every 0.5s for 6s...")
last_hwnd = None
for i in range(12):
    fg = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(fg)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(fg, buff, length + 1)
    title = buff.value
    
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
    try:
        pname = psutil.Process(pid.value).name()
    except Exception:
        pname = "unknown"
        
    ex_style = user32.GetWindowLongW(fg, -20)  # GWL_EXSTYLE
    is_topmost = bool(ex_style & 0x00000008)   # WS_EX_TOPMOST
    print(f"t={i*0.5:.1f}s | PID {pid.value:6} ({pname:20}) | Topmost: {str(is_topmost):5} | Title: {title[:50]}")
    time.sleep(0.5)
```

### 3. Enumerate Top-Level Visible Overlays

Detect hidden or borderless overlay windows covering the display:

```python
import ctypes
import psutil

user32 = ctypes.windll.user32

def enum_windows_proc(hwnd, lParam):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            
            rect = (ctypes.c_long * 4)()
            user32.GetWindowRect(hwnd, rect)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            
            ex_style = user32.GetWindowLongW(hwnd, -20)
            is_topmost = bool(ex_style & 0x00000008)
            is_iconic = user32.IsIconic(hwnd)
            
            if w > 50 and h > 50 and not is_iconic:
                try:
                    pname = psutil.Process(pid.value).name()
                except Exception:
                    pname = "unknown"
                print(f"{pname:25} | PID: {pid.value:6} | Rect: ({rect[0]},{rect[1]},{w}x{h}) | Topmost: {str(is_topmost):5} | Title: {title[:60]}")
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)
```

### 4. Correlate Running Processes with Hermes Cron Jobs

Identify which active cron job or background fleet runner is spawning the focus-stealing process tree:

```python
import psutil, os

# Filter out current python process
my_pid = os.getpid()
active_crons = []
for p in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid']):
    if p.info['pid'] == my_pid: continue
    cmd = ' '.join(p.info['cmdline'] or []).lower()
    if any(k in cmd for k in ['.ps1', 'runner', 'watchdog', 'supervisor', 'workflow']):
        try:
            parent = psutil.Process(p.info['ppid'])
            pname = f'{parent.name()}:{parent.pid}'
        except Exception:
            pname = 'unknown'
        active_crons.append((p.info['pid'], p.info['name'], pname, cmd[:120]))

for pid, name, parent, cmd in active_crons:
    print(f'[{pid:5}] {name:15} (PPID {parent:18}): {cmd}')
```

## Remediation Guidance

- **Overwolf / MetaTFT:** If playing TFT or League in borderless window, close Overwolf (`Stop-Process -Name Overwolf, OverwolfBrowser, OverwolfHelper -Force`) or disable auto-launch overlay hooks in MetaTFT settings.
- **Background Automation (User Rule: 'Game = tắt nháy, CẤM pause cron'):**
  - **DO NOT pause cron jobs** to solve game stutters or focus stealing unless explicitly ordered by user.
  - Fix the root cause of console flashing:
    1. Ensure all background PowerShell launchers specify `-WindowStyle Hidden` (e.g. `powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ...`).
    2. In Python scripts spawning CLI tools (`adb.exe`, `ffmpeg.exe`, `omp.cmd`, `cmd.exe`), enforce `creationflags=subprocess.CREATE_NO_WINDOW` (`0x08000000`) on all `subprocess.Popen` / `subprocess.run` calls.
    3. For running unhidden consoles, hide them dynamically using Win32 `ShowWindow(hwnd, 0 /* SW_HIDE */)`.
  - For ghost overlays (`cua-driver.exe` with `Cua.AgentCursorOverlay.default` 1920x1080): terminate idle/stale driver instances (`Stop-Process -Name cua-driver -Force`).
- **Stuck Helpers:** Terminate `Not Responding` Electron sub-processes.

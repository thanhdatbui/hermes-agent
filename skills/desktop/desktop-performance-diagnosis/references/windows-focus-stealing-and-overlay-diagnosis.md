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

## Remediation Guidance

- **Overwolf / MetaTFT:** If playing TFT or League in borderless window, close Overwolf (`Stop-Process -Name Overwolf, OverwolfBrowser, OverwolfHelper -Force`) or disable auto-launch overlay hooks in MetaTFT settings.
- **Background Automation:** Pause high-frequency GPM cron supervisors (`cronjob(action='pause')`) while gaming or working interactively on the primary desktop.
- **Stuck Helpers:** Terminate `Not Responding` Electron sub-processes.

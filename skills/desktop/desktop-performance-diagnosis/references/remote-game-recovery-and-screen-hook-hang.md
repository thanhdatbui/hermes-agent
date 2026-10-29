# Remote Game Recovery & Screen Hook Hang Diagnosis (Admin PC)

## Overview & Incident Patterns
When managing remote Windows gaming environments (e.g. `admin-farm` / `192.168.110.119`), client and game crashes (League of Legends, Teamfight Tactics / TFT) frequently manifest as "stuck in match" or unresponsive reconnect buttons rather than normal game termination.

## Root Cause: UltraViewer Graphic Hook Exception (`uvh64.dll`), Overwolf (`OWUtils.dll`) & Deadlock
1. **Graphic Hook Crash & Deadlock on Unreal Engine 5 Client:**
   Remote desktop control software like `UltraViewer_Desktop.exe` injects a screen-capturing hook (`uvh64.dll`). When the DirectX 12 / Unreal Engine 5 client (`TFTClient-Win64-Shipping.exe` or `LeagueClient.exe`) initializes, it calls `USER32.dll` and `UxTheme.dll` to construct the game window. The global message hook in `uvh64.dll` causes a total deadlock on `GameThread`, logging:
   `LogCore: Error: Hang detected on GameThread (thread hasn't sent a heartbeat for 25.00 seconds)`
   `0x00007ffc5f027d68 UnknownFunction []` -> Resolves via `VirtualQueryEx` + `GetMappedFileNameW` directly to `C:\Program Files (x86)\UltraViewer\uvh64.dll`.
   The game process remains alive (`MainWindowHandle: 0`, consuming ~1.2GB RAM and 10-15% CPU), showing only an empty/transparent icon on the Windows Taskbar, but the actual window never renders or opens.
2. **Third-Party Overlay Interference (Overwolf / OWUtils.dll):**
   Similarly, companion apps running on Overwolf (or standalone TFT overlays) inject `OWUtils.dll` into D3D12 swapchains. If Overwolf hangs or desyncs, it halts `GameThread` in the identical manner.
3. **WerFault Deadlock:**
   Windows automatically spawns `WerFault.exe` (Windows Error Reporting) to dump memory. `WerFault.exe` holds an exclusive handle on the crashed process and locks the desktop compositor thread, causing the Riot/League Client window to freeze in a "Reconnecting" or "Game is running" state. The "Reconnect" button appears unresponsive, and clicks from background scripts or user input are completely ignored.

## Electron Helper Auto-Resurrection Immunity (e.g. TFTAcademy)
When users complain that third-party helpers (like `TFTAcademy.exe` or Discord) keep re-enabling auto-startup on boot despite deleting their startup shortcuts:
- **Root Mechanism:** Electron applications invoke `app.setLoginItemSettings({ openAtLogin: true })` inside their runtime. Every time the app is launched or auto-updates, it silently re-inserts its entry into `HKCU:\Software\Microsoft\Windows\CurrentVersion\Run`.
- **Permanent Immunization (2-Layer Defense):**
  1. Delete the registry value: `Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "electron.app.TFTAcademy"`.
  2. Immunize via Explorer StartupApproved: Set the binary toggle in `HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run` for `"electron.app.TFTAcademy"` to `0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00`. Windows Explorer permanently enforces this disabled state even if the application rewrites its entry in the `Run` key.

## Safe Remediation Workflow via Remote SSH
Do not try to click "Reconnect" on an overlay-locked window. Follow this sequence:

```python
# 1. Kill the crash reporter and lingering game processes
for proc in ['WerFault.exe', 'TFTClient-Win64-Shipping.exe', 'TFTClient.exe', 'LeagueClientUxRender.exe', 'LeagueClientUx.exe', 'LeagueClient.exe', 'Riot Client.exe', 'RiotClientServices.exe']:
    os.system(f'taskkill /F /IM {proc} /T >nul 2>&1')

# 2. Terminate the offending screen hook software
os.system('taskkill /F /IM UltraViewer_Desktop.exe /T >nul 2>&1')
os.system('taskkill /F /IM uv_x64.exe /T >nul 2>&1')

# 3. Relaunch cleanly into interactive Session 1
# Note: Executing "start RiotClientServices.exe" from a non-interactive SSH terminal (Session 0)
# fails to display UI on the user's desktop. Use a transient scheduled task with /it /rl highest:
cmd = r'schtasks /create /tn "LaunchRiotClient" /tr "\"C:\Riot Games\Riot Client\RiotClientServices.exe\" --launch-product=teamfight_tactics --launch-patchline=pbe" /sc once /st 00:00 /f /it /rl highest'
subprocess.run(cmd, shell=True, capture_output=True)
subprocess.run('schtasks /run /tn "LaunchRiotClient"', shell=True, capture_output=True)
subprocess.run('schtasks /delete /tn "LaunchRiotClient" /f', shell=True, capture_output=True)
```

## Permanent Prevention: Disable UltraViewer Auto-Startup & Graphic Hook
To prevent recurrences after Windows reboots, UltraViewer's background service must be permanently disabled so it never starts automatically:
```powershell
# 1. Stop and permanently disable UltraViewer Windows Service
Stop-Service -Name 'UltraViewService' -Force -ErrorAction SilentlyContinue
Set-Service -Name 'UltraViewService' -StartupType Disabled

# 2. Check and remove any UltraViewer entries from Registry Run keys and Startup folders
# Run keys: HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run, HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
# Startup: C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup
```
### Post-Use Game Entry Protocol (No Reboot Required)
When the user finishes using UltraViewer remotely and wants to enter the game:
- **NO REBOOT IS REQUIRED**: Simply exit/close UltraViewer completely (`Right-click tray icon -> Exit` or `taskkill /F /IM UltraViewer* /T`).
- Once UltraViewer's GUI/Desktop process exits, `uvh64.dll` graphic hook unloads cleanly from memory.
- The user can launch Riot Client / TFT immediately without crashing. Because `UltraViewService` is set to `Disabled`, it will never resurrect in the background on subsequent boots.

## Visual Verification (Gate 6 Protocol)
Never report the game fixed based on exit codes alone.
1. Capture remote screenshot via `cua-driver call get_desktop_state`.
2. Transfer image to local storage and inspect using `browser_navigate` + `browser_vision`.
3. Confirm the Riot Client window displays the yellow **"CHƠI" (Play ▶)** button and correct patchline (e.g. "Teamfight Tactics PBE").

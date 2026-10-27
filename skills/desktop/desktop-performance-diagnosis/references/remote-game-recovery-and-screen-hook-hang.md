# Remote Game Recovery & Screen Hook Hang Diagnosis (Admin PC)

## Overview & Incident Patterns
When managing remote Windows gaming environments (e.g. `admin-farm` / `192.168.110.119`), client and game crashes (League of Legends, Teamfight Tactics / TFT) frequently manifest as "stuck in match" or unresponsive reconnect buttons rather than normal game termination.

## Root Cause: UltraViewer Graphic Hook Exception (`uvh64.dll`) & WerFault Deadlock
1. **Graphic Hook Crash:**
   Remote desktop control software like `UltraViewer_Desktop.exe` injects a screen-capturing hook (`uvh64.dll`). When the DirectX client (`TFTClient-Win64-Shipping.exe` or `LeagueClient.exe`) initializes, swaps resolution, or reconnects, the unloaded hook `uvh64.dll_unloaded` throws an Access Violation exception `0xc0000005` under `bad_module_info`.
2. **WerFault Deadlock:**
   Windows automatically spawns `WerFault.exe` (Windows Error Reporting) to dump memory. `WerFault.exe` holds an exclusive handle on the crashed process and locks the desktop compositor thread, causing the Riot/League Client window to freeze in a "Reconnecting" or "Game is running" state. The "Reconnect" button appears unresponsive, and clicks from background scripts or user input are completely ignored.

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

## Visual Verification (Gate 6 Protocol)
Never report the game fixed based on exit codes alone.
1. Capture remote screenshot via `cua-driver call get_desktop_state`.
2. Transfer image to local storage and inspect using `browser_navigate` + `browser_vision`.
3. Confirm the Riot Client window displays the yellow **"CHƠI" (Play ▶)** button and correct patchline (e.g. "Teamfight Tactics PBE").

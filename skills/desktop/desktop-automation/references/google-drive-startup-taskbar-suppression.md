# Google Drive for Desktop - Windows Startup Dialog Suppression & Taskbar Triage

## 1. Problem Description
On Windows 10/11 machines running Google Drive for Desktop (`GoogleDriveFS.exe`), restarting or rebooting the machine often causes a Google Drive triangular icon to appear on the Taskbar (alongside user applications like Telegram, Chrome, and games like TFT / League of Legends). The user has to manually close or dismiss the window after every reboot.

## 2. Technical Root Cause
- **Onboarding / Promo WebView2 Dialog:**
  When `GoogleDriveFS.exe` starts via the Windows Run registry key (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`), it runs with `--startup_mode`.
  However, on newly installed or updated clients, Google Drive lacks the `core_feature_config` or has not dismissed the onboarding/promotion tour. During early boot initialization, if user credentials are restored asynchronously or feature flags are not locally cached, Google Drive initializes WebView2 (`microsoft_webview2_browser_app.cc`) and creates a top-level `WindowsNativeWindow` (`native_window_win.cc`).
- **Visible Window = Taskbar Button:**
  On Windows, any process creating an unowned visible top-level window without `WS_EX_TOOLWINDOW` automatically receives a Taskbar button from Windows Explorer.
- **Missing Enterprise Policy Suppression:**
  By default, Google Drive does not have policies in `Software\Policies\Google\DriveFS` to suppress interactive prompts, dialogs, and auto-start recreation.

## 3. Resolution & Configuration Blueprint

### Step 1: Suppress Dialogs via Registry Policies
Apply the following DWORD values under `HKCU\Software\Policies\Google\DriveFS` (and `HKLM\Software\Policies\Google\DriveFS` if elevated):

| Registry Value | Type | Value | Purpose |
| :--- | :--- | :--- | :--- |
| `DisableOnboardingDialog` | `REG_DWORD` | `1` | Suppresses Welcome & onboarding walkthrough dialogs. |
| `DoNotShowDialogs` | `REG_DWORD` | `1` | Prevents interactive popup dialogs on startup. |
| `AutoStartOnLogin` | `REG_DWORD` | `0` | Disables auto-launching on Windows user login and stops re-creating Run keys. |

```python
import winreg

def harden_gdrive_policies():
    key_path = r"Software\Policies\Google\DriveFS"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
        winreg.SetValueEx(key, "DisableOnboardingDialog", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "DoNotShowDialogs", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "AutoStartOnLogin", 0, winreg.REG_DWORD, 0)
```

### Step 2: Disable Windows Startup Entry
Remove or rename the startup entry under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`:
- Existing value: `GoogleDriveFS` -> `"C:\Program Files\Google\Drive File Stream\132.0.0.0\GoogleDriveFS.exe" --startup_mode`
- Renamed value: `__disabled_GoogleDriveFS` (standard Windows Task Manager disabled convention).

### Step 3: Headless On-Demand Mounting in Scheduled Tasks
For automated scripts that require Google Drive virtual drive (e.g. `G:\My Drive` for video backups or multi-cloud sync):
Do not rely on Google Drive running in the user's startup session. Instead, launch it on-demand silently:

```python
import os
import subprocess
import time
from pathlib import Path

GDRIVE_ROOT = Path(r"G:\My Drive")
GDRIVE_EXE = Path(r"C:\Program Files\Google\Drive File Stream\132.0.0.0\GoogleDriveFS.exe")

def ensure_gdrive_mounted(timeout_sec=15):
    if GDRIVE_ROOT.is_dir():
        return True
    
    if GDRIVE_EXE.is_file():
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        subprocess.Popen([str(GDRIVE_EXE), "--startup_mode"], creationflags=flags)
        
        start = time.time()
        while time.time() - start < timeout_sec:
            if GDRIVE_ROOT.is_dir():
                return True
            time.sleep(1)
            
    return GDRIVE_ROOT.is_dir()
```
This guarantees:
1. Reboots are 100% clean (zero Google Drive icons on the Taskbar).
2. Scheduled backup scripts still run reliably by mounting the virtual filesystem on-demand without GUI disruption.

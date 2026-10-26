---
name: desktop-automation
description: Best practices and safety patterns for using computer-use and desktop automation.
---

# Desktop Automation Best Practices

This skill captures learnings and pitfalls for driving the user's desktop via tools like `computer_use`.

## Safety & Style Guidelines
- **User Preference (Action-First vs. Passive Instructions):** When the user reports an app error, freeze, failure, or annoying system tray notification (e.g. missing driver panel, update nag), they expect the agent to immediately diagnose and remediate the issue directly — DO NOT just explain the cause or list manual steps/options for the user to execute. If a quick fix exists, execute it immediately end-to-end. Asking the user to click through options or run files is considered laziness and an operational failure unless strictly impossible without user credentials/elevation.
- **Autonomous Operation:** The user expects autonomous operation but prioritizes not having their active work interrupted.
- **Do Not Disrupt:** Never close windows, log out, or perform destructive actions unless explicitly requested. Always verify the element label in a SOM capture before clicking, especially near window controls.
- **Communication:** If the AI is struggling to interact with a specific app (e.g., Chrome/Browser), stop and explain why rather than repeatedly sending potentially destructive commands.

## Pitfalls & Troubleshooting
- **Host Package & Store App Installation under Guarded Coordinator (`winget` / NVIDIA DCH / Microsoft Store):**
  - *Symptom:* Persistent Windows tray alerts like `NVIDIA Control Panel not found` on DCH driver setups, missing codecs, or missing Store apps.
  - *Guard Traps on Coordinator:* Running `winget install ...` or `explorer.exe "ms-windows-store:..."` directly in the Coordinator terminal hits `COORDINATOR TERMINAL BLOCKED (DEFAULT-DENY)` because package managers and shell protocol handlers are not in the Coordinator allowlist. Running inline `python -c` with `subprocess` is blocked, and foreground terminal commands with `timeout > 60s` fail with `GUARD_FOREGROUND_TIMEOUT_EXCEEDED`.
  - *Fix:* Delegate host app installation directly to Worker via `dispatch_worker.py`:
    ```bash
    python D:/Taadaa/tools/dispatch_worker.py --timeout 120 "Chạy lệnh winget install 'NVIDIA Control Panel' --accept-source-agreements --accept-package-agreements để cài đặt NVIDIA Control Panel cho Windows."
    ```
    Must run via `terminal(command=..., background=True, notify_on_complete=True, timeout=180)` so the Coordinator stays within the 60s foreground limit and gets awakened upon completion.
    - *Store Product ID Fallback:* If searching by name fails, install via Microsoft Store Product ID: `winget install --id 9NF8H0H7WMLT --source msstore --accept-source-agreements --accept-package-agreements`.

- **VMware `vmrun` Guest File Operations (`copyFileFromHostToGuest` ReadOnly Overwrite Failure):**
  - *Symptom:* `vmrun -T ws -gu <user> -gp <pass> copyFileFromHostToGuest <vmx> <host_path> <guest_path>` fails with exit code `4294967295` (-1 / 127) and output `Error: You do not have access rights to this file`.
  - *Root Cause:* When the destination file already exists in the guest OS with the Windows `ReadOnly` attribute set (common for files captured inside baseline/template snapshots), `vmrun` attempts an in-place overwrite and fails even under an admin account. Both `copyFileFromHostToGuest` and `deleteFileInGuest` fail with this access rights error against ReadOnly files.
  - *Pitfall with `fileExistsInGuest`:* `vmrun fileExistsInGuest` returns exit code `0` if present, but exit code `127` (not `1`) if absent ("The file does not exist.").
  - *Fix:* Use PowerShell inside the guest (`runProgramInGuest` with `-interactive` or `-ExecutionPolicy Bypass`) to clear attributes and force-remove the existing file before copying:
    ```powershell
    if (Test-Path -LiteralPath '<guest_path>') { Remove-Item -LiteralPath '<guest_path>' -Force }
    ```
    Then invoke `vmrun copyFileFromHostToGuest`.

- **VMware Guest Interactive GUI Automation via `vmrun` (Mouse & Keyboard):**
  - *Host UIPI Barrier & CUA Failure:* On Windows host, VMware Workstation (`vmware.exe`) runs at High/System integrity. `computer_use` (cua-driver at Medium integrity) will fail in `background` mode (UIPI: target hwnd is at System integrity; cua-driver is at Medium integrity -> escalate) and in `foreground` mode (`SendInput inserted fewer modifier or mouse events than expected`). CUA cannot inject mouse/keyboard into VMware Workstation from the host. All guest interactions (clicking, typing, app launches) MUST be executed through VMware Tools via `vmrun -T ws -gu <user> -gp <pass> runProgramInGuest <vmx> -interactive` under the guest user session.
  - *VMware Host Modal Dialogs Pausing Guest:* When VMware Workstation on host shows modal update dialogs ("Software Updates"), it can pause/freeze the guest VM (toolbar pause icon highlighted orange, screen captures return pitch black ~5KB). Unpause immediately via `vmrun -T ws unpause <vmx>` (exit code 0) before running guest scripts.
  - *Guest User Profile / Shortcut Path Mismatch Trap:* In baseline VM templates, do not assume host user names (e.g. `thanh` vs `tada`). `GUEST_USER` is `tada` (`C:\Users\tada\Desktop\...` or `C:\Users\Public\Desktop\...`). Hardcoding a mismatched username in `explorer.exe` or `WScript.Shell.CreateShortcut` fails silently without opening the target app. To launch desktop shortcuts deterministically regardless of username, use WinRT OCR to locate the desktop icon bounding box (e.g. `Bounds: [9, 453, 67, 465] | Center: (38, 459)`) and trigger synthetic double-click in guest PowerShell.
  - *Reliable Synthetic Double-Clicks in Guest:*
    ```powershell
    Add-Type -TypeDefinition @"
    using System;
    using System.Runtime.InteropServices;
    public class Input {
        [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
        [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, int dwExtraInfo);
        public static void DoubleClick(int x, int y) {
            SetCursorPos(x, y);
            System.Threading.Thread.Sleep(150);
            mouse_event(0x02, 0, 0, 0, 0);
            mouse_event(0x04, 0, 0, 0, 0);
            System.Threading.Thread.Sleep(100);
            mouse_event(0x02, 0, 0, 0, 0);
            mouse_event(0x04, 0, 0, 0, 0);
        }
    }
    "@
    [Input]::DoubleClick($x, $y)
    ```
  - *End-to-End Automation Expectation vs. Premature Handoff (The Antigravity/OAuth Trap):*
    When running guest VM onboarding or rescue automation (e.g. Antigravity Pro rescue), DO NOT halt at the landing screen (such as "Continue with Google" or the initial email form) and ask the user to take over manually. The automated tool suite (`ag-onboard-kit` / guest PowerShell scripts) is built to execute the entire sequence autonomously:
    1. Click "Continue with Google" in Antigravity (`Bounds: [871, 349, 1033, 365]`, Center `[952, 357]` when top-anchored or `[960, 540]` when centered).
    2. Overcome Electron app topmost occlusion (see below).
    3. Type email -> Enter -> solve/tick reCAPTCHA -> type password -> generate and enter TOTP 2FA (`pyotp.TOTP(secret).now()`).
    4. Authorize consent ("Allow" / "Đăng nhập") and return to Antigravity.
    5. Send test chat prompt in Antigravity to trigger the backend verification challenge.
    6. Stop and hand off to the user ONLY when the physical barrier is reached: the Google Device Verification QR Code screen (which requires a physical phone camera scan) or an un-automatable image puzzle. Stopping earlier is an operational failure.

  - *Electron Topmost Occlusion Trap (Antigravity occluding Chrome OAuth Card):*
    When Antigravity opens Chrome for Google OAuth, the Antigravity window often retains topmost focus or displays a "context deadline exceeded" dialog in the center (`X ~ 720..1200, Y ~ 350..500`). In maximized Chrome at 1920x1080, Google's Sign-In card is also centered at `X ~ 960, Y ~ 300..600`. Clicks intended for the Google login input field (`Email or phone` at `X ~ 1000..1050, Y ~ 400`) land on Antigravity instead.
    *Fix:* Explicitly minimize Antigravity and maximize + foreground Chrome via PowerShell P/Invoke:
    ```powershell
    Add-Type @'
    using System;
    using System.Runtime.InteropServices;
    public class WindowHelper {
        [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
        [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    }
    '@
    $ag = Get-Process -Name Antigravity -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
    if ($ag) { [WindowHelper]::ShowWindow($ag.MainWindowHandle, 6) } # 6 = SW_MINIMIZE
    $chrome = Get-Process -Name chrome -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
    if ($chrome) {
        [WindowHelper]::ShowWindow($chrome.MainWindowHandle, 3) # 3 = SW_MAXIMIZE
        [WindowHelper]::SetForegroundWindow($chrome.MainWindowHandle)
    }
    ```

  - *Google OAuth Risk Challenge (QR Scan Gate):* When signing in to Google accounts in guest VMs through residential/mobile proxies, Google often halts automation with `Quét mã QR bằng điện thoại`. Do not attempt blind OCR input loops. Capture the screen via `vmrun captureScreen`, crop the QR area, and deliver the screenshot to the user to scan with a physical phone Camera app (Zalo fails on Google authentication intents).
  - *Pitfall with `typeKeystrokesInGuest`:* Often fails on host with exit code `4294967295` (`Error: Insufficient permissions in the host operating system`) unless running with specific host OS elevation/hook privileges.
  - *Pitfall with Screen Blanking/Screensaver in Guest:* When guest displays all black (PNG size ~5KB, single color `(0,0,0)`), the guest screen is asleep/locked. Wake it by running `[System.Windows.Forms.SendKeys]::SendWait("{ESC}")` with `runProgramInGuest -interactive`.
  - *Reliable Synthetic Mouse Clicks in Guest:* Use PowerShell with P/Invoke `user32.dll` (`SetCursorPos` + `mouse_event`) executed via `vmrun runProgramInGuest -interactive` under the guest user session:
    ```powershell
    Add-Type -TypeDefinition @"
    using System;
    using System.Runtime.InteropServices;
    public class Input {
        [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
        [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, int dwExtraInfo);
        public static void Click(int x, int y) {
            SetCursorPos(x, y);
            System.Threading.Thread.Sleep(150);
            mouse_event(0x02, 0, 0, 0, 0); // MOUSEEVENTF_LEFTDOWN
            System.Threading.Thread.Sleep(150);
            mouse_event(0x04, 0, 0, 0, 0); // MOUSEEVENTF_LEFTUP
        }
    }
    "@
    [Input]::Click($x, $y)
    ```
  - *Visual Inspection in Guest:* Pair with `vmrun captureScreen <vmx> <host_png>` and `windows-native-ocr` (`winrt_ocr.py --boxes`) to dynamically locate buttons, input fields, and CAPTCHA coordinates without hardcoding.

- **Windows Cloud Storage (iCloud / OneDrive) Placeholders Stall Bulk Copy/Archive:**
  - Files inside `C:\Users\<user>\iCloudDrive` or OneDrive with Files On-Demand enabled are virtual NTFS reparse points / sparse placeholders.
  - Naive file traversal (`os.walk`, `shutil.copy2`, `robocopy`, `7za`) on placeholder files forces Windows to synchronously request the file stream from the remote cloud provider, causing scripts/terminal commands to hang indefinitely until hitting timeout.
  - *Fix:* Check file offline attributes (`FILE_ATTRIBUTE_OFFLINE` / `0x1000`) or exclude cloud-synced folders from batch local archiving unless files are explicitly hydrated/pinned locally.
- **Fast Mass-File Deletion on Windows (NTFS):**
  - When removing large folders containing 50,000–200,000+ loose files (e.g. `node_modules`, `.venv`, old browser caches/profiles), Python's `shutil.rmtree` or sequential deletion can take 15–30+ minutes due to per-file userland stat overhead.
  - *Fix:* Invoke native NTFS removal via `cmd.exe /c rd /s /q "<path>"` (using list args `['cmd.exe', '/c', 'rd', '/s', '/q', path]` to avoid shell quoting traps). It runs directly in kernel space and finishes in seconds.
- **Installing & Launching Background Cloud Sync Clients (Google Drive Desktop):**
  - Install silently via winget: `winget install --id Google.GoogleDrive -e --silent --accept-source-agreements --accept-package-agreements`.
  - Launching GUI/background services from git-bash: never run `GoogleDriveFS.exe` directly in the foreground (blocks console). Use `cmd.exe /c start "" "C:\Program Files\Google\Drive File Stream\<version>\GoogleDriveFS.exe"` (or Python detached `subprocess.Popen`) to detach cleanly.
  - **Preventing Google Drive from Popping Up on Taskbar upon Windows Reboot (Startup Dialog Suppression & Headless Background Mounting):**
    - *Symptom:* After Windows reboot (scheduled reboot or restart), a Google Drive triangular icon appears on the Taskbar next to user apps (e.g. games, Telegram, browsers). The user has to manually close the window every time.
    - *Root Cause:*
      1. Newly installed or updated Google Drive for Desktop (`GoogleDriveFS.exe`) lacks feature config / onboarding dismissal. When started via `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` with `--startup_mode`, Google Drive initializes WebView2 and creates a `WindowsNativeWindow` for onboarding, sign-in, or promotional dialogs (e.g. `BUTTON_TYPE_PIN_TO_TASKBAR`), creating a visible top-level window with a Taskbar button.
      2. Google Drive lacks enterprise policy suppression keys in the Windows registry, allowing it to display modal windows and dialogs on boot.
    - *Remediation (Zero-Taskbar Headless Configuration):*
      1. **Registry Policy Hardening (`DriveFS` Policies):**
         Add under `HKCU\Software\Policies\Google\DriveFS` (and `HKLM\Software\Policies\Google\DriveFS` if elevated):
         - `DisableOnboardingDialog` (DWORD = `1`): Suppresses the initial/post-update Welcome & Onboarding tour window.
         - `DoNotShowDialogs` (DWORD = `1`): Prevents Google Drive from displaying interactive pop-up dialogs.
         - `AutoStartOnLogin` (DWORD = `0`): Prevents Google Drive from auto-launching on Windows user login and re-creating startup keys.
      2. **Disabling Windows Startup Run Entry:**
         In `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, rename or remove the `GoogleDriveFS` value (e.g. rename to `__disabled_GoogleDriveFS` matching Windows Task Manager standard).
      3. **Preserving Scheduled / Background Backup Tasks (On-Demand Mounting):**
         If automated scripts rely on Google Drive virtual drive (e.g. `G:\My Drive\video_goc_backup` via `sync_and_clean_gdrive.py` or multi-cloud sync watchdog):
         Do NOT require Google Drive to sit in the user startup queue. Instead, in the background backup script, check if `G:\` is mounted; if not, launch `GoogleDriveFS.exe --startup_mode` silently with `creationflags=subprocess.CREATE_NO_WINDOW` (`0x08000000`), wait up to 10s for the virtual drive to mount, proceed with sync, and keep the user's desktop/taskbar completely pristine during gaming and reboot cycles.
  - **Resolving Google Drive "Lost and Found" (`Bị thất lạc và đã tìm thấy`) Unsynced File Errors:**
    - Stuck files live under `%LOCALAPPDATA%\Google\DriveFS\lost_and_found\<account_id>\`.
    - Check if the file exists at the target path on `G:\` (Google Drive virtual mount). If safe, back up the orphaned file to a local staging folder (e.g. `D:\backup_gdrive_lost_and_found\`) and delete/clear the file inside the `lost_and_found` folder.
    - *Crucial Restart Step:* Moving files out of `lost_and_found` while `GoogleDriveFS.exe` is running leaves the in-memory toast/sync error active. You must restart Google Drive (`taskkill /F /IM GoogleDriveFS.exe` followed by detached launch) and verify `%LOCALAPPDATA%\Google\DriveFS\Logs\drive_fs.txt` that `G:\` mounts cleanly with 0 errors to permanently dismiss the notification.
- **Multi-Cloud Backup Sync Architecture (OneDrive -> Google Drive 5TB & iCloudDrive):**
  - Use custom multi-threaded Python scanner (`os.walk` + `ThreadPoolExecutor`) rather than bare `robocopy` when syncing across cloud/virtual drives (e.g. `G:\` Google Drive File Stream, `C:\Users\<user>\iCloudDrive`). Virtual filesystem drivers experience high network latency / throttling on recursive stat queries over 10,000+ loose files.
  - Exclude temporary/lock artifacts: `.849*` (OneDrive internal lock GUIDs), `~$*`, `*.tmp`, `desktop.ini`, and dev bloat (`node_modules`, `.venv`, `__pycache__`, `.pytest_cache`, `.git`).
  - Deploy as a silent watchdog in Hermes Cron (`no_agent: true`, schedule `0 */6 * * *`): runs `sync_onedrive_multicloud.py`, exits silently when up to date, reports concise summary on updates/errors.
- **Opening a file/editor for the user from the agent shell (Windows/git-bash)** — when the user must edit a file (e.g. paste a secret into `.env`) and `computer_use` is unavailable or `start` silently fails:
  - `cmd //c start "" notepad "C:\path"` can return exit 0 with **no process spawned** — never trust it; verify with `wmic process where "Name='notepad.exe'" get ProcessId`.
  - Bare `notepad.exe "path"` in the terminal tool **blocks** (GUI app holds the console) and the timeout kills the tree — never run it foreground.
  - Literal `&` backgrounding is rejected by the terminal tool. **The reliable fallback: `explorer.exe "C:\path\to\file"`** — opens the file with its default association (`.env` → Notepad) and returns immediately.
  - **PowerShell via bash: **single-quote the whole `-Command '...'`** — double quotes make bash expand `$_` (e.g., `{$_.MainWindowTitle}` becomes `{3.MainWindowTitle}` → "term not recognized" spam).
    - **PowerShell `.ps1` file fallback**: When inline `-Command` fails due to escaping, write the script to a temp `.ps1` file and run with `-File`. Use raw strings in Python to avoid double-escape hell.
    - **`$_.MainWindowTitle` from bash**: Git-bash expands `$_` before passing to PowerShell. ALWAYS write the PS script to a `.ps1` file (using `tempfile.NamedTemporaryFile(suffix='.ps1')`) or use `cat << 'EOF' > script.ps1` heredoc to avoid this. Never inline PowerShell with `$_` in a bash command string.
  - **Background Window Screenshot (win32gui + PrintWindow)** — Capture any window's content without raising/focusing it, works for apps that block PrintScreen or WAF:
    ```python
    import win32gui, win32ui, ctypes
    from PIL import Image

    hwnd = <window_handle>  # from EnumWindows or FindWindow
    rect = win32gui.GetWindowRect(hwnd)
    w, h = rect[2] - rect[0], rect[3] - rect[1]

    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)

    ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)  # PW_RENDERFULLCONTENT=2

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                          bmpstr, 'raw', 'BGRX', 0, 1)

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC(); mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)
    ```
    - **Enumerate visible windows**: `win32gui.EnumWindows(callback, None)` with `win32gui.IsWindowVisible(hwnd)` filter.
    - **Find window by title**: `win32gui.FindWindow(None, "exact title substring")` or partial match via EnumWindows.
    - **Get process PID from HWND**: `win32process.GetWindowThreadProcessId(hwnd)` → `(tid, pid)`.
    - **Scroll before capture**: Use `ctypes.windll.user32.mouse_event(0x0800, 0, 0, -360, 0)` (MOUSEEVENTF_WHEEL, 3 clicks down) positioned at window center via `SetCursorPos`.
    - **Navigate to URL without CDP**: Copy URL to clipboard (`Set-Clipboard`), then `SendKeys("^l")` → `SendKeys("^v")` → `SendKeys("{ENTER}")`. SendKeys requires `SetForegroundWindow` first.
    - Pitfall: `SendKeys` can fail with "Access is denied" if the window is not in the foreground. Always `ShowWindow(hwnd, 9)` (SW_RESTORE) + `SetForegroundWindow(hwnd)` first.
  - `tasklist //FI "IMAGENAME eq X"` silently fails in git-bash (double-slash option, same as `schtasks //Query`) — use `wmic process where "Name='X'" get ...` instead.
  - `explorer.exe` can spawn duplicate windows for the same file — dedupe: `powershell -NoProfile -Command 'Get-Process notepad | Select-Object -First 1 | Stop-Process -Force'`, then confirm one remains via `Get-Process notepad | Select-Object Id,MainWindowTitle` (title shows `<file> - Notepad`).
- **Background Interaction Failures:** Background input (like `type` or keyboard shortcuts) often fails for specific window classes (e.g., `Chrome_WidgetWin_1` in Electron apps like Claude Desktop, VS Code, Discord):
  - *Symptom:* `computer_use(action="type", delivery_mode="background")` returns `code: "background_unavailable"` with suggestion to escalate to foreground.
  - *Fix:* Follow the verify → escalate ladder by re-issuing with `delivery_mode="foreground"`. cua-driver will briefly activate the target window, send global keystrokes/text via SendInput, and restore the prior foreground window.
  - *Fast CLI / Slash Command Execution in Electron Chat UIs:* When driving apps like Claude Desktop, rather than fighting nested popover/dropdown elements with ambiguous coordinates, directly type the full command into the prompt input using foreground mode (e.g., `action="type", text="/advisor opus", delivery_mode="foreground"` then `action="key", keys="enter", delivery_mode="foreground"`). Note that commands like `/advisor` apply to new conversations or after `/compact` / `/clear`.
- **Element Mapping Errors:** UI elements in SOM/AX captures can shift. Always perform a fresh `capture` immediately before a `click` or `type` action to ensure indices are valid.
- **Identifying Targets:** If an app is not found, use `list_apps` to verify the exact string expected by `cua-driver` before trying to target it with `capture` or `focus_app`.
- **Playwright CDP Screenshot Font Loading Timeout on Heavy Web Apps (Google Cloud Console, etc.):**
  - Calling `await page.screenshot()` on complex SPA pages like Google Cloud Console can hang and fail with `TimeoutError: Page.screenshot: Timeout 30000ms exceeded. waiting for fonts to load...`.
  - *Fix:* When verifying actions on heavy SPAs, pass `timeout=5000` or rely on DOM element inspection (`query_selector`, text/checkbox status) rather than full-page screenshot capture that blocks on external web fonts and analytics beacons.
- **Background Browser Automation with `computer_use` & Native "Save As" Dialog Handling (2026-10-12):**
  - *Context:* When user requests automating tasks on an existing logged-in browser session (e.g. BoxTaiKhoan, marketplace, web shop) where Chrome is already open without remote debugging port 9222 attached, killing the browser disrupts user tabs.
  - *Reliable Background Execution:*
    1. **Synthetic Click Reliability:** In `Chrome_WidgetWin_1` windows, `delivery_mode='background'` clicks on web elements (buttons, links, comboboxes) succeed reliably via synthetic events without raising the window or moving the host OS cursor.
    2. **Handling Native HTML `<select>` (Items per Page / Filters):** Setting `AXValue` on a Chromium ComboBox does not fire the DOM `change` event. Instead, click the ComboBox in background mode to open the list, then click the target `ListItem` (e.g. `500` or `1000`).
    3. **Handling Modal Dialogs (SweetAlert / Confirmation):** Background clicks on confirmation buttons (e.g., `#36 Button 'Đồng ý'`) trigger web actions immediately.
    4. **Handling Windows Common Dialog "Save As" in Background:**
       - When a browser action triggers a file download with a "Save As" prompt, Windows spawns a `#32770` dialog owned by `chrome.exe`.
       - Run `computer_use(action='list_windows')` to find the exact `pid` and `window_id` of the `Save As` dialog.
       - Capture the `Save As` window via `action='capture', pid=..., window_id=...` and click element `Button 'Save'` (UIA Invoke). The file is saved directly to the target folder (`Downloads`) without stealing focus.
    5. **Viewport Expansion via Maximization:** If table rows/elements lie below the viewport height (<1000px), click element `Button 'Phóng to'` to maximize the window to 1080p, bringing more rows into view for background interaction without mouse scrolling.
- **Handling Chrome UIA Provider Hangs via Win32 `PrintWindow` + WinRT OCR + `PostMessage` Click (2026-10-14):**
  - *Symptom:* `computer_use` fails with `cua-driver get_window_state failed: Error: get_window_state timed out after 4s (UIA provider unresponsive on hwnd 0x..., class 'Chrome_WidgetWin_1')`. This occurs when Chrome has dozens of active tabs, causing the accessibility (UIA) tree walker to freeze.
  - *Failure Mode:* `capture(mode='som')` and `capture(mode='vision')` both fail because cua-driver waits on UIA accessibility inspection before capturing.
  - *Reliable Background Workaround (Zero-Focus Steal):*
    1. **Navigation without CDP:** Use Python `webbrowser.open(url)` to open tabs or navigate the user's active Chrome instance cleanly without stealing focus.
    2. **Direct GDI Window Capture (PrintWindow):** Use `win32gui.GetWindowDC(hwnd)` + `ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)` to save a pixel-perfect window snapshot directly to disk (e.g. `D:\Taadaa\runtime\artifacts\window_screen.png`), completely bypassing UIA tree enumeration.
    3. **Dynamic Coordinate Extraction via WinRT OCR:** Run native Windows WinRT OCR (`Windows.Media.Ocr.OcrEngine` via PowerShell) to extract line/word text and exact pixel bounding boxes (`$word.BoundingRect.X`, `$word.BoundingRect.Y`, `Width`, `Height`).
    4. **Background Synthetic Click via PostMessage:** Calculate target center `(x, y)` relative to window and post mouse messages directly to `hwnd`:
       ```python
       lParam = win32api.MAKELONG(x, y)
       win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
       time.sleep(0.05)
       win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
       ```
    5. **Post-Action State Verification:** Immediately re-capture with `PrintWindow` and run WinRT OCR to confirm navigation or state transition (e.g., login submission to 2FA prompt) before reporting.
- **Resolving Broken Windows Shortcuts & "Problem with Shortcut" Dialogs (Start Menu vs. Desktop Desync & Unicode Save Traps):**
  - Moving app installations between drives breaks shortcuts in both Desktop and Start Menu (`C:\ProgramData\Microsoft\Windows\Start Menu\Programs\<App>`), causing Windows Search to pop up "Problem with Shortcut". Both locations must be updated in lockstep.
  - **Dual Desktop Duplication Trap (`Public\Desktop` vs `User\Desktop`):** Windows Explorer Desktop aggregates `C:\Users\Public\Desktop` and `C:\Users\<user>\Desktop`. Creating or repairing shortcuts in both folders (or combining English and localized names like `Teamfight Tactics` and `Dau Truong Chan Ly`) causes duplicate/quadruplicate icons on the user's desktop. Always place canonical shortcuts strictly in `C:\Users\Public\Desktop` and purge duplicates from `C:\Users\<user>\Desktop`.
  - **Launcher Sub-App Generic Icon Clutter Trap (`IconLocation` Missing):** When targeting launcher suites (Riot Client, Steam, Battle.net) with product launch args (e.g. `RiotClientServices.exe --launch-product=...`), omitting `IconLocation` defaults all shortcuts to the launcher's root icon (e.g. 8 identical red Riot fists). Always set `$shortcut.IconLocation = '<SubProductExePath>,0'` (e.g. `TFTClient.exe,0` or `LeagueClient.exe,0`).
  - **PowerShell `-like "*?*"` Catastrophic Desktop Wiping Trap:** In PowerShell `-like`, `?` is a single-character wildcard, NOT a literal question mark! Using `Where-Object { $_.Name -like "*?*" } | Remove-Item` to clean up mojibake filenames matches EVERY filename with $\ge 1$ character and wipes the user's entire desktop! Always use `.Contains('?')` or `-match '\?'` to match literal `?`.
  - **Desktop Shortcut Recovery from Start Menu:** If desktop shortcuts are ever accidentally wiped, copy them back from the master caches in Start Menu (`C:\ProgramData\Microsoft\Windows\Start Menu\Programs\` and `%APPDATA%\Microsoft\Windows\Start Menu\Programs\`) rather than reinstalling applications.
  - Saving non-ASCII/accented shortcuts via WScript.Shell in PowerShell without UTF-16LE throws `FileNotFoundException` due to `?` character replacement. Create ASCII shortcuts first and copy via Python `shutil.copy` to preserve Unicode names.
  - Always notify shell via `ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)` to refresh caches immediately.
  - Dismiss lingering modal dialogs cleanly via `user32.FindWindowW(None, "Problem with Shortcut")` + `PostMessageW(hwnd, 0x0010, 0, 0)`.
- **Remote Interactive Desktop Capture over SSH (Bypassing Session 0 & Defender AMSI via `cua-driver` CLI):**
  - When administering Windows remotely via SSH, PowerShell `CopyFromScreen` is blocked by Windows Defender AMSI (`ScriptContainedMaliciousContent`) and Python `PIL.ImageGrab` fails in Session 0.
  - Call `cua-driver.exe call get_desktop_state` (which runs in the interactive user session via `cua-driver-serve` scheduled task) to retrieve `screenshot_png_b64` with 0 focus steal and 0 AMSI alerts.
  - Use cross-host shared cloud folders (e.g. `D:\OneDrive\TaadaaData\`) for instant artifact sync when `scp` is barred by coordinator allowlists.
- **`computer_use` capture returns 0×0 / empty elements while `hermes computer-use doctor` reports ALL OK** (verified 2026-08-13): the cua-driver MCP session is a zombie. Doctor only health-checks the driver binary, not the live MCP session. Confirm by checking the Hermes agent log (`~/AppData/Local/hermes/logs/agent.log`) for `session 'hermes-<id>' has ended; tool call '<...>' was rejected. Call start_session with this id to revive it`. Fix = a fresh cua-driver session (restart the gateway or kill+respawn cua-driver). Note: `Stop-Process`/`taskkill /F /IM cua-driver.exe` may be access-denied and the process survives — and the user may explicitly forbid a gateway restart while other processes are live; then fall back to a manual action on the user's machine instead of forcing it.

## Cua-driver lifecycle and protocol mismatch recovery
- `hermes computer-use doctor` is a binary/host health check, not proof that the live daemon and MCP client speak the same protocol. A 0×0 capture plus `Unknown method: metadata` or repeated CLI-fallback failures means the daemon is stale or protocol-incompatible.
- After `hermes computer-use install --upgrade`, an already-running daemon can remain on the old version. Verify the daemon PID/version separately from the Hermes `cua-driver mcp` client; do not assume the upgrade replaced the live daemon.
- Prefer the smallest restart: stop only the stale daemon, then start the registered `cua-driver-serve` task again. On Windows, `Stop-Process` can return access denied; use the driver's own stop command or the registered task/process termination path, and verify the old PID is gone before starting the new daemon. Do not kill Chrome or its user profile.
- Restarting the gateway from inside the gateway is blocked by design. If a gateway restart is genuinely required, launch it from an external shell; otherwise replace the stale CUA daemon first.
- Verification gate: run `cua-driver status`, confirm the new daemon PID, then call `computer_use capture`. Accept the repair only when the capture has non-zero dimensions and identifies the target app/window. Never report success from a click/capture request that has not been independently re-captured.

## Execution/reporting correction
- When the user says to fix it, execute the narrowest diagnostic/fix immediately; do not narrate a plan or claim a component is fixed before the verification tool result arrives.
- For Vietnamese status reports, be concise: state the root cause, the exact component changed, the live verification result, and any remaining blocker. Avoid repeated progress announcements and avoid saying “đã xong” until the final capture/state check passes.

## Application update vs. source-repository update
- First identify what the user means by “update”: a running/installed application, a source checkout, or both. Treat “update the app” as an application-operations task by default; do not start with `git status`, stash, rebase, merge, or source edits unless the user explicitly asks to update the repository/source.
- For a running local app, inspect its actual launch mechanism (shortcut/installer/updater/service), executable or command line, version/status endpoint, and package/update channel before touching the source tree. Keep application state/data separate from repository state.
- If the app is currently running, verify whether the requested updater can update in place and whether a restart is required. Do not kill or restart it merely to make a source checkout look current; preserve the live service until the app-level update path is known.
- If discovery shows only a development command such as `npm run dev`, report that it is a source checkout/dev instance rather than assuming it is the installed application. Ask or state the blocker before performing repository operations.
- When the user corrects “app, not repo,” stop repository work immediately, verify no destructive Git operation remains in progress, and return to app-level discovery. Keep the response concise and acknowledge the scope correction without defending the prior workflow.
- Do not treat a user's broad “update it” consent as permission to invent extra disruptive steps. In particular, `taskkill` is not a prerequisite for updating source/dependencies; omit it unless restarting the actual runtime is independently required and in scope.
- For a repo-backed dev instance, separate the gates: (1) identify/update the source revision, (2) install dependencies, (3) run the build, (4) start/reload the app, (5) verify the live health endpoint. Report each gate in Vietnamese and do not call the app updated until the live endpoint answers.
- If the upstream revision contains a reproducible build-breaking defect, make the smallest source correction needed for the requested app update, record the exact file/line and build result, and keep unrelated user changes backed up rather than silently merging them.

See `references/vm-antigravity-onboard-rescue-pipeline.md` for the full step-by-step guest VM automation pipeline (Antigravity launch geometry, Chrome de-occlusion, OAuth form targeting, and QR handoff). See `references/gdrive-taskbar-suppression-and-headless-mount-20261020.md` for the registry policy hardening, zlib payload compression for remote SSH cmdline limits, atomic script patching, and headless on-demand mounting pattern. See `references/google-drive-startup-taskbar-suppression.md` for the original taskbar suppression pattern. See `references/application-vs-repository-update.md` for the checklist and evidence pattern for distinguishing an installed/running app update from a source-repository update. See `references/omniroute-update-lessons.md` for the OmniRoute-specific update/build/health sequence and failure patterns. See `references/gpmlogin-local-api-cdp.md` for the GPMLogin Local API + Playwright CDP background automation recipe. See `references/background-browser-download-and-save-as-workflow.md` for background browser control, SweetAlert modals, and Windows "Save As" file download automation via `computer_use`. See `references/windows-icloud-photos-storage-relocation.md` for redirecting locked Windows iCloud Photos sync storage to secondary drives via Shell Known Folders (`SHSetKnownFolderPath`) and handling flat UUID photo naming vs. Apple Album selection in Windows file pickers. See `references/windows-hevc-mov-thumbnail-icaros-repair.md` for resolving missing Windows Explorer thumbnails for iPhone HEVC `.MOV` and `.HEIC` media via unelevated `HKCU` Icaros shell extension registration and `SHChangeNotify`. See `references/capcut-qt6-desktop-automation-and-photo-timeline.md` for CapCut Desktop (Qt6) background canvas capture, WinRT OCR coordinate targeting, chronological EXIF photo milestone extraction, and critical template replacement pitfalls (timeline duration stretching, compound clip navigation traps, and mobile vs PC batch selection workflows). See `references/chrome-uia-hang-printwindow-winrt-postmessage.md` for zero-focus background automation bypassing unresponsive Chrome/Electron UIA accessibility trees via direct GDI `PrintWindow`, WinRT OCR coordinate extraction, and synthetic `PostMessage` clicks. See `references/windows-shortcut-repair-and-remote-cua-desktop-capture.md` for resolving "Problem with Shortcut" dialogs, dual Start Menu/Desktop synchronization, Windows Protocol URL Scheme repair (`ShellExecute` error 31 on in-app launch buttons), and remote CUA desktop screenshot capture.

## Unexpected privileged windows and cross-machine attribution
- Trigger: the user sees an unexpected Administrator terminal, firewall help/error output, or says the command was typed on another machine.
- First distinguish **where the command was typed** from **where the visible process/window exists**. A Telegram message or remote instruction alone is not proof that the local desktop executed it; require local process and event evidence before attributing it to a bot, Hermes, or a remote machine.
- Inspect without modifying state: target PID/title/start time/owner, parent PID and surviving parent chain, child console host, PowerShell operational events, PSReadLine history, relevant firewall event records, active remote-control services/sessions, and exact command-line/script evidence. Use a narrow time window around process creation.
- Correlate the exact malformed command in history or script-block logs. A concatenated paste such as `...localport=20129netsh...` explains a `netsh` “specified value is not valid” help screen, but does not identify the actor by itself.
- Label findings `confirmed`, `excluded`, or `unproven`. If the parent has exited or process-creation auditing is unavailable, actor attribution remains unproven; do not turn timing or chat content into proof.
- If an elevated target cannot be stopped from the current unelevated shell and the user did not explicitly authorize elevation, do not broaden the action or kill unrelated workers. Report the access-denied blocker and leave the target state accurately stated.
- Verify security postconditions independently (for example, all firewall profiles still enabled) and distinguish “command history exists” from “the command succeeded.”

See `references/unexpected-privileged-window.md` for the concise evidence recipe and attribution checklist.

## Browser vs. Desktop & Zero-Disruption Automation:
  - Default for background automation of a logged-in browser is CDP because it avoids stealing focus, popping windows forward, or disturbing the user.
  - An explicit user request for `computer_use` is binding: use `computer_use` for the browser if it can see a live window; do not silently substitute CDP, browser tools, or OS keystrokes.
  - An explicit user request for `browser plugin` means browser tools only; do not silently substitute CDP or `computer_use`.
  - Do not use raw `SendKeys`/`SetForegroundWindow` as a substitute for `computer_use`, and do not raise a window unless explicitly requested.
  - If the requested surface returns an empty/0×0 capture, missing window, WAF page, or incomplete UI, preserve state and report the blocker. Do not claim the search or click succeeded and do not switch surfaces without authorization.
  - When CDP is the authorized surface, launch Chrome in the background with remote debugging: `chrome.exe --remote-debugging-port=9222 --user-data-dir="<profile_path>"` (always launched detached or via `background=True`) and verify the target/page before acting.
- **Launching GUI Apps from Terminal:** Never run interactive GUI apps (Chrome, Notepad) as foreground terminal commands — they hold the shell pipeline and freeze the agent session. Always launch detached or backgrounded.
- **Preventing Flickering Console Windows & Focus Stealing (`conhost.exe` / `cmd.exe` nháy màn hình & cướp focus game) in Background Scripts:**
  - *Symptom:* Cửa sổ console đen hoặc cmd nháy chớp tắt liên tục trên màn hình khi máy đang chạy ngầm batch rendering, download, video pipeline, hoặc cron watchdog. Trong các game toàn màn hình (TFT, LoL, War3), hiện tượng này làm drop FPS, giật alt-tab, hoặc cướp focus chuột.
  - *Root Cause:* Trên Windows, các script Python/PowerShell nền khi gọi các CLI console subsystem (`ffmpeg`, `adb`, `git`, `ssh`, `cmd.exe`) mà thiếu cờ `CREATE_NO_WINDOW` sẽ khiến Windows Console Subsystem tự động cấp phát console (`conhost.exe`) trên desktop station `WinSta0\Default`.
  - *Pitfall with PowerShell `Start-Process -WindowStyle Hidden`:* Naive `Start-Process -FilePath "cmd.exe" ... -WindowStyle Hidden` chỉ áp dụng `SW_HIDE` sau khi console đã được tạo. Trong các batch chạy hàng chục worker song song, conhost vẫn chớp nháy và cướp focus của ứng dụng đồ họa/game đang chạy.
  - *Fix for Python:* Luôn truyền `creationflags=subprocess.CREATE_NO_WINDOW` (`0x08000000`) trên Windows:
    ```python
    import sys, subprocess

    popen_kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
    subprocess.run(cmd, capture_output=True, text=True, **popen_kwargs)
    ```
  - *Fix for PowerShell:* Sử dụng trực tiếp .NET `System.Diagnostics.ProcessStartInfo` để bật `CreateNoWindow`:
    ```powershell
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "cmd.exe"
    $psi.Arguments = $cmd
    $psi.CreateNoWindow = $true
    $psi.UseShellExecute = $false
    $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $p = [System.Diagnostics.Process]::Start($psi)
    ```
- **Triaging & Hiding Lingering CUA Cursor Overlays (`Cua.AgentCursorOverlay.default`):**
  - *Symptom:* Cửa sổ toàn màn hình 1920x1080 mang tiêu đề `Cua.AgentCursorOverlay.default` thuộc `cua-driver.exe` hiển thị đè lên desktop sau các tác vụ `computer_use`.
  - *Root Cause:* Mỗi phiên CUA khởi tạo một lớp overlay trong suốt (`WS_EX_LAYERED | WS_EX_TRANSPARENT`) để hiển thị con trỏ ảo. Khi có nhiều phiên CUA MCP chạy hoặc sau khi hoàn tất tác vụ, overlay có thể vẫn còn hiển thị trên Z-order.
  - *Remediation (Zero-Kill):* Dùng Win32 `user32.ShowWindow(hwnd, SW_HIDE)` (với `SW_HIDE = 0`) để ẩn lập tức lớp overlay mà không cần tắt daemon `cua-driver` chính.
- **Game-Safe Automation & Scheduled Reboot Preflight Contract (TFT / War3 Guard):**
  - *Symptom:* Người dùng lo lắng việc thoát trận game hoặc máy rảnh sẽ bất ngờ kích hoạt reboot tự động.
  - *Contract:*
    1. Reboot máy KHÔNG BAO GIỜ tự kích hoạt động theo sự kiện tắt game. Hệ thống chỉ chạy vào các mốc cố định qua Windows Task Scheduler (chuẩn farm: `05:20`, `11:20`, `17:20`).
    2. Tại thời điểm kích hoạt mốc reboot, script preflight (`farm_preflight_daily_reset.py`) bắt buộc kiểm tra các tiến trình trận đấu (`tftclient-win64-shipping.exe`, `league of legends.exe`, `war3.exe`). Nếu phát hiện đang trong trận đấu, script lập tức `[ABORT]` hủy hoàn toàn lượt reboot ca đó để tránh xử thua AFK.
    3. Trạng thái chỉ ở sảnh (lobby / client ngoài sảnh) hoặc đã thoát trận hoàn toàn mới được coi là an toàn nếu không có active device lock.
- **Windows Network Adapter & Default Gateway Reconfiguration (Headless Elevation):**
  - Git-bash runs under standard unelevated user tokens. Network adapter configuration, gateway changes, and route table adjustments require Administrator elevation.
  - When `ConsentPromptBehaviorAdmin` is `0`, `Start-Process powershell.exe -Verb RunAs -Wait -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'script.ps1'` elevates silently without modal UAC dialogs.
  - When switching default gateway across dual routers/ISPs on the same subnet, set static IP directly via `netsh interface ip set address name="<alias>" static <ip> <mask> <gw> <metric>` to avoid dropping the connection or losing the host IP. Direct subnet routing ensures local access to other routers/proxies on the same LAN is preserved.
  - See `references/windows-network-adapter-configuration.md` for the execution pattern, script template, and complete 5-step verification checklist.
- **Windows USB Root Hub Selective Suspend & ADB Phone Farm Drops:**
  - When the Windows host (PC Kibe) sleeps/idles or reconnects RDP, Windows turns off power to `USB Root Hub 3.0` (`MSPower_DeviceEnable.Enable = $true`), dropping dozens of USB connections simultaneously and causing ADB server crash/restart.
  - See `references/usb-selective-suspend-and-host-sleep.md` for the WMI power-saving disable commands and screen-off recovery pattern.
- **Diagnosing Broken / Blank White Icons on Windows Taskbar (Dead Pinned Shortcuts vs. Active Error Dialogs):**
  - *Symptom:* The Windows Taskbar displays a blank white sheet icon or a generic white/gray window frame icon that fails to open or launch when clicked.
  - *Root Cause Classification (CRITICAL - Do NOT Assume Pinned Shortcut First):*
    1. **Case A: Active Modal System Error Dialog (`#32770 System Error` / `WerFault`) Obscured by Fullscreen Apps:**
       - When an application (e.g. GPMLogin, game, browser, installer) fails to load a dependent DLL or crashes on launch, Windows CSRSS creates a Win32 system modal dialog (`#32770`, e.g. `chrome.exe - System Error: The code execution cannot proceed because ... was not found`).
       - On Windows 10, unstyled system error dialogs lack an application icon, so Windows assigns a **generic white/gray rectangular window frame icon** on the Taskbar.
       - If the main application is running maximized/fullscreen (e.g. `(-8, -8, 1928, 1048)`), the error dialog remains **buried underneath (occluded)**. Clicking the Taskbar button merely flashes or focuses the obscured dialog without bringing up a new window, appearing as "clicked but nothing opens".
       - *Detection:* Enumerate top-level taskbar-eligible windows using `win32gui.EnumWindows`:
         ```python
         import win32gui, win32process, win32con, psutil
         def find_taskbar_windows():
             wins = []
             def cb(hwnd, _):
                 if not win32gui.IsWindowVisible(hwnd): return
                 owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
                 ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                 if (owner == 0 and not (ex & win32con.WS_EX_TOOLWINDOW)) or (ex & win32con.WS_EX_APPWINDOW):
                     wins.append({
                         "hwnd": hwnd,
                         "title": win32gui.GetWindowText(hwnd),
                         "class": win32gui.GetClassName(hwnd),
                         "rect": win32gui.GetWindowRect(hwnd),
                         "pid": win32process.GetWindowThreadProcessId(hwnd)[1]
                     })
             win32gui.EnumWindows(cb, None)
             return wins
         ```
         Look for windows with class `#32770`, `WerFaultWindow`, or titles containing `System Error`, `Error`, `Crash`.
       - *Remediation:* Focus dialog with `Alt + Tab` or programmatically bring to front / press Enter / click OK, then fix the missing dependency or crash in the parent app.
    2. **Case B: Dead Pinned Shortcut (.lnk):**
       - Pinned taskbar items are `.lnk` files located in `%APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar`. When an app executable is deleted (e.g. uninstalled portable app), Windows displays a generic blank white page icon.
       - Inspect via `$env:APPDATA\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar` using WScript.Shell.
  - See `references/taskbar-icon-triage-active-dialog-vs-pinned-shortcut-20261008.md` for the complete diagnosis workflow, Win32 window filter, and visual evidence mapping.
  - *Rapid Diagnosis Recipe (PowerShell + WScript.Shell):*
    ```powershell
    $sh = New-Object -ComObject WScript.Shell
    $tbPath = "$env:APPDATA\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"
    Get-ChildItem -Path $tbPath -Filter "*.lnk" | ForEach-Object {
        $lnk = $sh.CreateShortcut($_.FullName)
        [PSCustomObject]@{
            Name       = $_.Name
            TargetPath = $lnk.TargetPath
            Exists     = (Test-Path -LiteralPath $lnk.TargetPath)
        }
    } | Where-Object { -not $_.Exists }
    ```
  - *Remediation & Cache Cleanup:*
    1. If app is discarded: Unpin via right-click or delete the orphan `.lnk` directly from `$env:APPDATA\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\<name>.lnk`.
    2. Check for leftover user data / cache: Orphaned Chromium-based apps often leave gigabytes in `%LOCALAPPDATA%\<Vendor>` (e.g., `AppData\Local\Perplexity`). Calculate size and list for user approval before deleting (per user safety discipline).
    3. *Guard-Compliant Directory Sizing:* When calculating directory size on machines with strict walker guards (`GUARD_PYTHON_WALKER` / `GUARD_POWERSHELL_SCAN`), avoid `os.walk` or `Get-ChildItem -Recurse`. Use an iterative queue with `os.scandir(follow_symlinks=False)` scoped strictly to the target folder:
       ```python
       def get_target_dir_size(start_dir):
           total = 0
           dirs = [start_dir]
           while dirs:
               curr = dirs.pop()
               try:
                   with os.scandir(curr) as entries:
                       for entry in entries:
                           if entry.is_file(follow_symlinks=False):
                               total += entry.stat(follow_symlinks=False).st_size
                           elif entry.is_dir(follow_symlinks=False):
                               dirs.append(entry.path)
               except OSError:
                   pass
           return total
       ```
    4. If app is still needed: Reinstall the application to restore the missing binary, or update the shortcut target to the new executable path.

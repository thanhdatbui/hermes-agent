# VMware Antigravity Validation Rescue & Session Isolation

## Context & Architecture
When Google flags an Antigravity Pro account with `VALIDATION_REQUIRED` (upstream 403 `Verify your account to continue` despite OmniRoute showing green active quota), web session OAuth and GPM Chrome profiles often fail to clear the device verification challenge because the challenge is tied to the Antigravity desktop application fingerprint and the device's assigned residential proxy.

The rescue harness lives under:
- **Scripts:** `D:\Taadaa\GPM auto\scripts\antigravity_rescue\`
  - `rescue_antigravity_start.py <email>`: Main entrypoint to revert VM snapshot, configure TUN proxy, and start Antigravity.
  - `vm_rescue_lib.py`: Helper library wrapping `vmrun.exe`, OmniRoute API, and sing-box configuration.
  - `vm_prelogin_gmail.py`: Helper to pre-login credentials and 2FA TOTP into Chrome in guest if needed.
- **VM VMX:** `D:\VM\ag-onboard\ag-onboard.vmx`
- **Snapshot Baseline:** `baseline-v2.17`
- **Kit Directory:** `D:\VM\ag-onboard-kit\` (mounted/copied to `C:\ag-kit` in guest).

---

## Key Pitfalls & Invariants

### 1. `runProgramInGuest` Background Execution & `-noWait`
- **Problem:** `start_tun_in_guest()` runs `start-tun2.ps1` inside the VM, which launches sing-box and polls `https://ifconfig.me/ip` up to 60s to confirm egress proxy change. Calling `vmrun runProgramInGuest` synchronously without `-noWait` and with a small `timeout` (e.g. 15s) causes Python `subprocess.TimeoutExpired`.
- **Rule:** Background daemons or initialization scripts in the guest MUST be launched using `-noWait` so `vmrun` returns immediately. The host then polls the guest log file (`C:\tun_<port>_log.txt`) until `OK - toan bo VM dang di qua proxy` is recorded.

### 2. Session 0 GUI Isolation vs. Active Desktop User (`thanh` vs. `tada`)
- **Problem:** In Windows, VMware Workstation `vmrun runProgramInGuest` without `-interactive` runs programs in **Session 0** (non-interactive service session), making GUI windows completely invisible on the virtual display and breaking UI automation / OCR.
- **Problem 2:** Even with `-interactive`, if `vmrun` credentials (`-gu tada -gp Ag123456`) differ from the currently logged-in desktop user (`thanh`), directly launching user-scoped binaries (e.g. `C:\Users\tada\AppData\Local\...`) fails with `A file was not found`.
- **Rule:**
  - The interactive desktop user in `ag-onboard` is `thanh` (`C:\Users\thanh\Desktop\Antigravity.lnk`).
  - To reliably launch Antigravity on the active user's desktop, invoke via the Windows shell:
    ```bash
    vmrun -T ws -gu tada -gp Ag123456 runProgramInGuest "D:\VM\ag-onboard\ag-onboard.vmx" -noWait "C:\Windows\explorer.exe" "C:\Users\thanh\Desktop\Antigravity.lnk"
    ```

### 3. Base32 TOTP Secret Padding Bug
- **Problem:** In `master_gmail_manager.xlsx`, column index 2 is Password, column 3 is Recovery Email, column 4 is 2FA Secret. In naive TOTP helpers, hardcoding `base64.b32decode(secret.upper() + "======")` breaks whenever `len(secret) % 8 == 0` (e.g. standard 32-character secrets become 38 chars, throwing `binascii.Error: Incorrect padding`).
- **Rule:** Always dynamically compute padding:
  ```python
  clean = secret.replace(" ", "").strip().upper()
  missing = len(clean) % 8
  if missing:
      clean += "=" * (8 - missing)
  secret_bytes = base64.b32decode(clean)
  ```

### 4. Idle Guest Screen Blanking on `captureScreen`
- **Problem:** If the VM is idle, Windows 10 turns off the virtual display or activates screensaver, causing `vmrun captureScreen` to produce a ~5KB completely black image, causing OCR to return empty results.
- **Rule:** Always wake the guest display before capturing by dispatching a synthetic mouse event:
  ```powershell
  Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class W { [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, int e); public static void Wake() { mouse_event(0x0001, 10, 10, 0, 0); } }'; [W]::Wake()
  ```

### 5. QR Verification Challenge & Real Phone Camera Rule
- **Rule:** When the Google device verification screen (`Xác minh thông tin để tiếp tục`) appears in Antigravity/Chrome, crop the QR code and send `MEDIA:<path>` to the operator.
- The operator MUST scan the QR using the native camera app on a real mobile device (iPhone/Samsung).
- **CẤM:** Do not scan via third-party in-app scanners (like Zalo), as Zalo strips session headers and breaks the Google TL verification token.

### 6. Chrome Pre-Login Sequence & Full 2FA Credential Discipline
- **Sequence Invariant (Chrome First, Antigravity OAuth Second):**
  - Always sign in to the Google account in Chrome inside the VM *first* before opening Antigravity to do OAuth.
  - When Chrome already holds active Google cookies, clicking "Continue with Google" in Antigravity either authorizes immediately or cleanly triggers the device verification challenge without getting stuck in blank loading or unhandled onboarding dialogues.
  - Open Chrome directly on the interactive desktop via `explorer.exe "https://accounts.google.com/signin"` rather than relying on brittle Playwright installations in the guest.
- **Credential Hand-off Invariant (Anti-Lazy 2FA Reporting):**
  - If a step cannot be 100% automated or is handed off to the operator, NEVER lazily report that "2FA will be generated when needed".
  - **BẮT BUỘC** must provide the full credential set:
    1. Email
    2. Password
    3. Recovery Email
    4. Base32 TOTP Secret (so the operator can import it into Authenticator / 2FAS)
    5. Live TOTP code (current, +30s, +60s) with remaining seconds.
- **Chrome Path Discovery in Guest:**
  - Do not hardcode `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe` in guest scripts. On 64-bit Windows guests, Chrome is frequently installed under `C:\Program Files\Google\Chrome\Application\chrome.exe`. Always check both paths or invoke via `explorer.exe <url>`.

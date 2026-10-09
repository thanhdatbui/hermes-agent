# Antigravity Pro & Free Pool Automation Runbook (VM Rescue & Quota Lifecycle)

## 1. Overview & Tooling Architecture
Antigravity accounts in OmniRoute (`http://127.0.0.1:20129`) are routed across:
- **`g1-pro-tier`** (Pro subscription): Has access to Claude Sonnet/Opus 4.6, Gemini 3.8/3.7/3.6 Flash & 3.1 Pro.
- **`free-tier`** / **`standard-tier`**: Basic quotas, fallback models.

When Google locks an account with `403 VALIDATION_REQUIRED` ("Verify your account to continue"), generic web browser OAuth from host does NOT clear it. It requires:
1. **VM Isolated Environment**: VMware Workstation VM (`D:\VM\ag-onboard\ag-onboard.vmx`), snapshot `baseline-v2.17`.
2. **Dedicated Mobile Proxy**: Routed via sing-box TUN inside the VM to the account's assigned S7 proxy (`test.taadaa.click:<port>` from `master_gmail_manager.xlsx`).
3. **Real Desktop Client**: Antigravity desktop app (v2.17.0) running inside the VM with Chrome set as default browser.

---

## 2. VM Automation via `vmrun` & PowerShell GUI Driving

### A. Overwriting Read-Only Kit Files in Guest
- **Problem**: Baseline snapshot kit files under `C:\ag-kit\` and `C:\ag-kit\sing-box\` carry Windows `ReadOnly, Archive` attributes. Direct `copyFileFromHostToGuest` or `deleteFileInGuest` via `vmrun` fails with:
  `Error: You do not have access rights to this file (exit code 4294967295 / -1)`.
- **Solution**: Execute a forced deletion script via PowerShell in guest prior to copying:
  ```powershell
  if (Test-Path -LiteralPath '<guest_path>') { Remove-Item -LiteralPath '<guest_path>' -Force }
  ```

### B. Interactive Desktop GUI Driving without Mouse Hardware Hook
`vmrun runProgramInGuest -interactive` allows sending clicks and keystrokes to the user session (`tada` / Session 1):
```powershell
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class Input {
    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")]
    public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, int dwExtraInfo);
    public static void Click(int x, int y) {
        SetCursorPos(x, y);
        System.Threading.Thread.Sleep(150);
        mouse_event(0x02, 0, 0, 0, 0); // LEFTDOWN
        System.Threading.Thread.Sleep(150);
        mouse_event(0x04, 0, 0, 0, 0); // LEFTUP
    }
}
"@
Add-Type -AssemblyName System.Windows.Forms
[Input]::Click($X, $Y)
[System.Windows.Forms.SendKeys]::SendWait($Text)
```

---

## 3. End-to-End Account Rescue Sequence

1. **Scan Accounts First**:
   Always run `python scan_pro_accounts.py` before touching the VM. Do not rescue accounts that only have `QUOTA_EXHAUSTED` (429) — only rescue true `BLOCKED` (403 `VALIDATION_REQUIRED`).
2. **Initialize VM & Proxy**:
   Run `python rescue_antigravity_start.py <email>`. It validates tier, starts TUN proxy, and launches the app.
3. **Automated Onboarding Navigation**:
   - Click "Continue with Google".
   - Chrome opens OAuth URL. Enter email, click Next.
   - If reCAPTCHA appears:
     - Checkbox is clicked via coordinate automation.
     - If audio challenge is available, automated solving via speech-to-text (`pydub` + `speech_recognition`) can bypass audio challenges.
   - Enter password from `master_gmail_manager.xlsx`.
   - Enter 2FA TOTP code generated dynamically via `pyotp.TOTP(secret).now()`.
   - Grant OAuth permissions ("Đăng nhập" / "Allow") and click "Open Antigravity".
4. **Triggering Google Device QR Challenge**:
   - In Antigravity app, send a message or select a model that triggers `Verification Required`.
   - Click **"Complete verification"** in the app banner.
   - Chrome opens the official Google device verification challenge (`accounts.google.com/v3/signin/challenge/iap/qrcode...`).
   - Dismiss any Chrome popups ("Restore pages?") by clicking Close or pressing ESC.
   - Capture clean screenshot of the QR code (`captureScreen`).
   - Deliver QR image via `MEDIA:<path>` for scanning.
   - **Crucial Rule**: Scan MUST be done using native phone camera (Samsung/iPhone). **Never use Zalo** as it silently fails Google's verification URL.
5. **Finalize & Snapshot**:
   Once verified, run `python verify_and_finalize.py <email>`:
   - Tests chat in isolation (`isolated_chat_test`).
   - Sets `isActive: True` in OmniRoute.
   - Takes VM snapshot `<email_prefix>-verified`.

---

## 4. Upgrading Free / Standard Accounts to Pro Pool in OmniRoute

When an account is upgraded to Pro externally:
1. Fetch provider details via `GET /api/providers`.
2. Update connection properties via `PUT /api/providers/<id>`:
   ```json
   {
     "isActive": true,
     "providerSpecificData": {
       "tier": "g1-pro-tier",
       "subscriptionTier": "Antigravity Pro",
       "plan": "Antigravity Pro"
     }
   }
   ```
3. Verify account via isolated chat test:
   ```bash
   python -c "import vm_rescue_lib as lib; print(lib.isolated_chat_test('<id>', model='antigravity/gemini-3.8-flash-tiered'))"
   ```

# Antigravity VM Onboarding & Rescue Pipeline Automation

## Context & Objectives
Rescuing Antigravity Pro accounts stuck on Google's `403 VALIDATION_REQUIRED` ("Verify your account to continue") requires signing into the real Antigravity desktop app running inside the `ag-onboard` VM (`D:\VM\ag-onboard\ag-onboard.vmx`) routed through the account's assigned residential/mobile S7 proxy.

## End-to-End Execution Protocol (Zero Premature Handoff)

### 1. Preflight & TUN Proxy Setup
1. Look up the account proxy port from `master_gmail_manager.xlsx`.
2. Revert VM to `baseline-v2.17` and start guest OS via `vmrun`.
3. In guest OS, start sing-box TUN (`start-tun.ps1 <port>`). Verify egress IP matches proxy IP.

### 2. Antigravity Launch & Window Geometry
1. Launch Antigravity via desktop shortcut or binary path.
   - Shortcut: `C:\Users\thanh\Desktop\Antigravity.lnk` (Windows user directory is `thanh`, vmrun guest user is `tada`).
2. Verify "Welcome to Antigravity" window:
   - Centered: Blue button `[G] Continue with Google` is at `X ~ 960, Y ~ 540`.
   - Top-anchored: Blue button is at `X ~ 952, Y ~ 357`.
3. Click `Continue with Google` via synthetic mouse event in guest:
   ```powershell
   [Input]::Click($x, $y)
   ```

### 3. Window De-Occlusion & Google OAuth Login
When Chrome AG opens the OAuth URL, Antigravity often remains centered on top with "context deadline exceeded". Chrome must be brought to the foreground and maximized:
```powershell
# Minimize Antigravity to remove occlusion
$ag = Get-Process -Name Antigravity -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if ($ag) { [WindowHelper]::ShowWindow($ag.MainWindowHandle, 6) }

# Maximize Chrome to full 1920x1080
$chrome = Get-Process -Name chrome -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if ($chrome) {
    [WindowHelper]::ShowWindow($chrome.MainWindowHandle, 3)
    [WindowHelper]::SetForegroundWindow($chrome.MainWindowHandle)
}
```

### 4. Form Filling & reCAPTCHA Handling
1. In maximized Chrome, Google Sign-In card is centered:
   - `Email or phone` input: `X = 1050, Y = 400`
   - `Next` button: `X = 1405, Y = 601`
2. Enter email via `SendKeys` (`^a` -> type email -> click `Next`).
3. If reCAPTCHA appears ("Confirm you're not a robot"):
   - Checkbox is at `X = 1010, Y = 432`. Click to tick.
   - If image challenge appears ("Select all images with ..."): crop challenge area `(580, 150, 1000, 750)` and alert user for quick visual selection.
4. Enter password (`type_password.ps1`).
5. Calculate TOTP 2FA code via `pyotp.TOTP(secret).now()` and enter (`type_2fa.ps1`).
6. Click "Đăng nhập" / "Allow" consent button (`click_allow.ps1` at `X = 815, Y = 480`).

### 5. Transition to Antigravity Chat & QR Code Extraction
1. Click `Open Antigravity` in Chrome external protocol prompt (`open_ag2.ps1` at `X = 568, Y = 260`) and kill Chrome.
2. In Antigravity, click chat input (`X = 842, Y = 420`), type test message `hi` and press Enter.
3. Chat response returns `Error Verification Required`.
4. Click `Learn more` / `Complete verification` (`X = 1100, Y = 735` or `X = 1384, Y = 766`).
5. Chrome opens the Google Device Verification QR Code page.
6. **Handoff Point**: Capture screen, crop QR code, inspect via `browser_vision` / OCR, and send `MEDIA:<qr_path>` to the user to scan with their physical phone Camera app.

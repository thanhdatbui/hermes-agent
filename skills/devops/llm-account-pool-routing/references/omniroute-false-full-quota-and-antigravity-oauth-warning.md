# False Full Quota Illusion, Stale Grant Pitfall & Antigravity OAuth Warning Bypass

## 1. The "100% Full Quota" Dashboard Illusion vs Upstream 403 / project_route_error

### Symptom
- OmniRoute / 9Router web dashboard shows a green indicator:
  - `Antigravity • Pro`
  - `Token expires in 0h 53m` (or active)
  - `Gemini 3.1 Flash Lite: 100% left` (with a **slashed-eye icon** / disabled toggle)
  - `Claude Opus 4 6 Thinking: 100% left` (with a **slashed-eye icon** / disabled toggle)
  - `Claude Sonnet 4 6: 100% left` (with a **slashed-eye icon** / disabled toggle)
- BUT actual requests to the model fail with:
  ```json
  [403]: Antigravity upstream error (403)
  error_type: project_route_error / insufficient_quota
  ```
- Meanwhile, AGY CLI's `pool_state.json` incorrectly flags the account as:
  ```json
  AGY_ERROR: {"short_error":"RESOURCE_EXHAUSTED (code 429): Individual quota reached. Please upgrade your plan"}
  ```

### Root Cause
1. **Zero-Token Consumption Freeze**: When Google blocks requests with `403 PERMISSION_DENIED` (`reason: VALIDATION_REQUIRED`), Google terminates the stream before any tokens are generated. Since 0 tokens were consumed, OmniRoute's quota snapshot never decrements and remains frozen at "100% left".
2. **Slashed-Eye Icon on UI**: The slashed-eye icon next to the models signals that OmniRoute's router has excluded / locked out these models on this specific connection due to the repeated upstream 403 errors, despite the displayed 100% quota.
3. **Local Quota Accounting**: OmniRoute/9Router UI calculates "100% left" by measuring tokens consumed in `call_logs` against plan limit. If an account is newly provisioned or has 0 successful calls, it calculates 0 usage -> displays 100% remaining regardless of whether the OAuth credentials are alive or dead!
4. **Local Token Expiry Calculation**: "Token expires in Xm" is calculated against `token_expires_at` column in SQLite `provider_connections`, not a live heartbeat to Google.
5. **Stale Refresh Token (`invalid_grant`)**: When an account was activated on Google One Pro, but the coordinator copied an old connection ID or token from 1+ months ago without running fresh OAuth:
   - Google Cloud Code rejects expired access token with 401.
   - OmniRoute calls `https://oauth2.googleapis.com/token` to refresh.
   - Google rejects refresh token with `HTTP 400: {"error": "invalid_grant", "error_description": "Bad Request"}`.
   - OmniRoute classifies upstream 401/403 as `project_route_error`.
   - AGY CLI throws the dead account into a 30m-2h 429 cooldown.

### Diagnostic Rule & Fast Extraction
- **NEVER trust dashboard 100% quota bar** when investigating failures. Look for the slashed-eye icon as the visual confirmation of upstream lockout.
- Check SQLite `call_logs` for `status = 403` and `error_type = 'project_route_error'`.
- Fast extraction of the latest Google `validation_url` directly from `omniroute-stdout.log`:
  ```python
  import re
  log_path = r'C:\Users\Kibe\AppData\Roaming\omniroute\logs\omniroute-stdout.log'
  with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
      for line in reversed(f.readlines()):
          if 'VALIDATION_REQUIRED' in line and '<email_or_conn_id>' in line:
              m = re.search(r'https://accounts\.google\.com[^\s",}]+', line)
              if m:
                  print("Validation URL:", m.group(0))
                  break
  ```

---

## 2. Google Antigravity OAuth Automation Flow via GPM CDP

When re-authorizing or onboarding a Google account to Antigravity via Playwright CDP on a GPM profile:

### Required Sequence & Selectors

1. **Step 1: Account Chooser (`accounts.google.com/v3/signin/accountchooser`)**
   - Click the account element:
     ```javascript
     document.querySelector('[data-identifier*="<email>"]') || 
     Array.from(document.querySelectorAll('li, div[role="link"]')).find(e => e.innerText.includes('<email>'));
     ```
2. **Step 2: 2FA TOTP Prompt (`accounts.google.com/v3/signin/challenge/totp`)**
   - Locator: `input[type="tel"], input#totpPin, input[name="totpPin"]`
   - Generate TOTP code: `pyotp.TOTP(clean_secret).now()`
   - Submit: `button:has-text("Tiếp theo"), button:has-text("Next"), #totpNext` or `Enter`.
3. **Step 3 (CRITICAL): Third-Party Warning Page**
   - Google often displays a security notice for Antigravity:
     > *"Đảm bảo rằng bạn đã tải ứng dụng này xuống từ Google... Đừng đăng nhập vào Google Antigravity trừ phi bạn chắc chắn..."*
     > *(Make sure you downloaded this app from Google... Do not sign in to Google Antigravity unless you are sure...)*
   - **Action**: Must click the explicit login confirmation button:
     - Selector: `button:has-text("Đăng nhập"), button:has-text("Sign in")`
     - Failing to handle this keeps the browser hanging on GlifWebSignIn.
4. **Step 4: Scopes & Consent Screen**
   - Select all scopes if checkbox exists: `#select-all-scopes`, `input[type="checkbox"]#select-all`.
   - Click consent button:
     - Selectors: `button:has-text("Cho phép"), button:has-text("Tiếp tục"), button:has-text("Allow"), button:has-text("Continue"), #submit_approve_access`.
5. **Step 5: Callback & Token Exchange**
   - Intercept `/callback?code=...` via `page.on("request")` or `page.on("response")`.
   - Send `POST http://127.0.0.1:20129/api/oauth/antigravity/exchange` with payload:
     `{code, redirectUri, codeVerifier, state}`.

---

## 3. Dual-Pool Ingestion & Verification Checklist

After token exchange succeeds (`HTTP 200`):
1. **Update OmniRoute DB (`storage.sqlite`)**:
   - `provider_connections`: set `provider_specific_data` JSON to `{"clientProfile": "ide", "projectId": "aicode-consumers", "tier": "g1-pro-tier", "plan": "Pro", "subscriptionTier": "Google AI Pro"}`.
   - `proxy_assignments`: assign dedicated mobile proxy ID corresponding to the account's machine port.
   - `combos`: ensure model `antigravity/gemini-3.8-flash-tiered` with `connectionId` is registered under `ag-gemini-pool-3`.
2. **Sync AGY CLI Sandbox**:
   - Run `python D:/Taadaa/tools/setup_agy_profile_creds.py`.
   - Check `D:/Taadaa/agy_profiles/pool_state.json`: if the profile had a cooldown due to prior failures, reset `cooldown_until: 0` and `reason: "Reauthenticated fresh token"`.
3. **Live Probe Verification**:
   - Run real inference:
     ```bash
     python D:/Taadaa/tools/ag_cli.py ask --profile <profile_name> --model gemini-3.8-flash-medium "Reply with exact word LIVE_CONFIRMED"
     ```
   - Verify stdout returns `LIVE_CONFIRMED`. Never declare DONE without verified probe output.

---

## 4. Web Session Cookie vs OAuth API Token Disconnect

### The Fallacy
"The account has an active session in GPM, and Google One Pro was successfully activated on the web, so why did the API request fail?"

### The Reality
- **Web Cookie Session** (`accounts.google.com`, `one.google.com`):
  - Manages browser-based access and Google One plan entitlement.
  - Clicking "Kích hoạt gói" on `one.google.com` upgrades the account to Google AI Pro 5TB on the web.
- **OAuth API Token** (`oauth2.googleapis.com`, Antigravity `cloud-platform` scopes):
  - Completely separate from web cookies.
  - Requires explicit consent grant via OAuth 2.0 flow.
  - Google Cloud Platform scopes (`https://www.googleapis.com/auth/cloud-platform`) enforce high-security verification: even with an active web session, Google prompts for 2FA TOTP and displays the third-party warning screen.
  - Activating a Google One Pro package on the web **DOES NOT** update, refresh, or resurrect an expired/revoked OAuth refresh token in OmniRoute.
- **Rule**: Whenever an account is upgraded to Pro via GPM web session, the agent **MUST IMMEDIATELY** execute the OAuth Antigravity flow in the same GPM profile to mint fresh tokens. Never assume a live web session translates to live API tokens.

---

## 5. End-to-End Autonomous Pipeline Pattern (Sniper → GPM Activate → OAuth → Dual Pool)

When autonomously acquiring and onboarding Google Gemini Pro accounts:
1. **Stock Polling & HMAC Buy**:
   - Poll product API every ~700ms with HMAC-SHA256 signature (`X-Tele-API-ID`, `X-Timestamp`, `X-Nonce`, `X-Signature`).
   - Immediately capture activation link on HTTP 200.
2. **GPM Profile Activation via CDP**:
   - Connect Playwright to GPM remote debugging address.
   - Navigate to activation URL, dismiss popups, and click `Kích hoạt gói`.
   - Take Gate 6 screenshot verifying celebration page (`Bạn là thành viên gói Google AI Pro`).
3. **Sequential OAuth Antigravity Authorization**:
   - Immediately navigate to OmniRoute `/api/oauth/antigravity/authorize`.
   - Select account -> Fill 2FA TOTP -> Click "Đăng nhập" on Antigravity security warning -> Grant consent -> Capture Authorization Code.
   - Send code to `/api/oauth/antigravity/exchange`.
4. **Dual-Pool Ingestion**:
   - **OmniRoute**: Update `provider_connections` (`tier: "g1-pro-tier"`, `plan: "Pro"`), assign 1:1 mobile proxy port in `proxy_assignments`, add to combo `ag-gemini-pool-3`.
   - **AGY CLI**: Initialize profile (`init-profile <name> --proxy <proxy_url>`), copy sandbox configs (`settings.json`, `projects.json`, `state.json`), run `setup_agy_profile_creds.py`, reset cooldown to 0 in `pool_state.json`.
5. **Live Verification Gate**:
   - Run focused inference probe: `python D:/Taadaa/tools/ag_cli.py ask --profile <profile> --model gemini-3.8-flash-medium "Reply with exact word PRO_CONFIRMED"`.
   - Only advance to the next account after receiving exact confirmation string.

---

## 6. Google Cloud Code VALIDATION_REQUIRED (403 PERMISSION_DENIED) & ALL_TARGETS_SKIPPED

### Symptom
- OmniRoute combo fails immediately with `ALL_TARGETS_SKIPPED: Every target was skipped before dispatch (capability pre-filter narrowed the pool and the remaining targets were all quota-exhausted/unavailable)`.
- The dashboard shows **100% quota remaining** because 0 tokens were consumed by requests.
- Inspecting `omniroute-stdout.log` reveals:
  ```json
  [Antigravity] Error Response - URL: https://daily-cloudcode-pa.googleapis.com/v1internal:streamGenerateContent
  Body: {
    "error": {
      "code": 403,
      "message": "Verify your account to continue.",
      "status": "PERMISSION_DENIED",
      "details": [{
        "reason": "VALIDATION_REQUIRED",
        "domain": "cloudcode-pa.googleapis.com",
        "metadata": {
          "validation_url": "https://accounts.google.com/v3/signin/continue?plt=...&continue=https://developers.google.com/gemini-code-assist/auth/auth_success_gemini"
        }
      }]
    }
  }
  ```

### Root Cause
Google Cloud Code requires periodic browser validation when account IP/proxy shifts or web session signs out. Google returns 403 `VALIDATION_REQUIRED` along with an explicit `validation_url`. OmniRoute treats 403 as target unavailable, leading to combo skip.

### CRITICAL DISTINCTION: OAuth Re-Auth vs Validation Recovery
- **OAuth Flow (`/api/oauth/antigravity/authorize`) IS NOT Validation Fix**: Re-running the OAuth consent screen and exchanging code for token only refreshes the OAuth access/refresh token in OmniRoute. It DOES NOT lift Google's `VALIDATION_REQUIRED` block on the Google Cloud Code backend.
- **The False-Live Verification Trap**: Sending a test request to OmniRoute with `forcedConnectionId` can silently fallback to another working account in the pool (e.g., returning HTTP 200 with another account). Never trust `forcedConnectionId` without verifying `call_logs` in `storage.sqlite` to prove the target `connection_id` actually served the request.
- **Why GPM Profile Fails on Deep Validation**: While simple session expiries can be clicked through with "Thử lại", true device-verification challenges hang on `uplevelingstep/selection` in a standard browser. Clearing these requires the full Antigravity desktop client under the matching S7 proxy/TUN (Section 9 VMware Rescue Pipeline) to trigger the native device QR code challenge.

### Deterministic Recovery Workflow
1. Extract `validation_url` from `omniroute-stdout.log`.
2. Connect to the account's GPM profile via Playwright CDP (`skip_proxy_check=true`).
3. Navigate directly to `validation_url`.
4. Page shows: *"Phiên của bạn đã kết thúc vì không có hoạt động. Hãy thử đăng nhập lại"*.
5. The button element is `<button>` with text **`Thử lại`** (or `Đăng nhập lại`).
6. Click the button -> Google validates the session and immediately redirects to `https://developers.google.com/gemini-code-assist/auth/auth_success_gemini` (*"Xác thực thành công | Gemini Code Assist | Google for Developers"*).
7. `VALIDATION_REQUIRED` flag is lifted instantly on Google upstream. The account resumes serving requests without token re-minting.
8. **QR Code Fallback for Mobile Verification**:
   If the operator needs to verify the account on their phone or if headless browser prompt hangs, generate a QR code image of `validation_url`:
   ```python
   import qrcode
   qr = qrcode.QRCode(version=1, box_size=10, border=4)
   qr.add_data(validation_url)
   qr.make(fit=True)
   img = qr.make_image(fill_color="black", back_color="white")
   img.save(r"D:\Taadaa\logs\verify_qr.png")
   ```
   Provide the QR code image via `MEDIA:` so the operator can scan it directly with the mobile device holding the account.

---

## 7. Google One AI Pro Link Activation Pitfalls & Schema Contracts

### 5-Minute Link Warranty & Mandatory GPM Preflight Gate (CRITICAL)
- **Hard Reality**: Promo/activation links from third-party shops (e.g. SumiStore) have an aggressive warranty window (typically **5 minutes** from timestamp of purchase).
- **The Stale Purchase Pitfall**: If an agent purchases a link before verifying that the target GPM profile is logged in and ready:
  1. Profile opens to `accounts.google.com/signin` (logged out).
  2. Entering email, password, and 2FA TOTP takes 2-5 minutes or gets interrupted.
  3. The activation link expires or gets invalidated past the 5-minute window. Google One permanently rejects the token, redirecting to `g1_landing_page=5` (the 15GB landing page), and the purchase is wasted with no shop warranty.
- **MANDATORY PREFLIGHT INVARIANT**:
  Before triggering `execute_buy()`, the script MUST launch the target GPM profile and verify:
  1. `one.google.com/home` loads with an active Google session (URL does not contain `signin` or `about`).
  2. `families.google/families/` loads cleanly without redirecting to `family/details`.
  If ANY check fails: **DO NOT BUY**. Abort or switch to a verified live profile immediately.

### Family Group Ineligibility Gate
- **Hard Rule**: Accounts participating in an existing Google family group **CANNOT** redeem Google One AI Pro promotion/family activation links.
- **Pre-Activation Check**: Navigate to `https://families.google/families/` in GPM profile.
  - If URL redirects to `https://myaccount.google.com/family/details`, the account is **already in a family** -> Google One activation link will bounce to `g1_landing_page=5` (the 15GB landing page) without applying the promo.
  - Only accounts showing `https://families.google/families/` (*"Bắt đầu tạo nhóm gia đình"*) are eligible.

### GDS Interstitial Screen Bypass
When signing in during activation, Google often intercepts with:
1. `gds.google.com/web/recoveryoptions` (*"Account Recovery Options"* / *"Xác nhận tùy chọn khôi phục"*): Click button `Lưu` (Save).
2. `gds.google.com/web/homeaddress` (*"Đặt địa chỉ nhà riêng"*): Click button `Để sau` or `Bỏ qua`.
- Once dismissed, the browser lands directly on `one.google.com/activate-plan/subscription/new/...` where the confirmation button (`Kích hoạt gói` / `Xác nhận`) can be clicked.

---

## 8. The "model_cooldown" False Quota-Exhausted Illusion vs Upstream 403

### The False Quota Exhausted Trap
When an account hits upstream 403 `VALIDATION_REQUIRED` repeatedly, OmniRoute caches an internal `model_cooldown` on `gemini-3.8-flash-tiered`.
Subsequent requests or automated scanner probes (such as `scan_pro_accounts.py`) receive:
```json
{
  "error": {
    "message": "All credentials for model gemini-3.8-flash-tiered are cooling down",
    "type": "rate_limit_error",
    "code": "model_cooldown",
    "reset_seconds": 120
  }
}
```
**CRITICAL PITFALL**: If an automated scanner simply checks `if "cooling down" in err: return "QUOTA_EXHAUSTED"`, it will falsely classify brand-new, newly-upgraded Pro accounts as "out of quota"!
- **The Reality**: The account was just upgraded to Pro, has `used: 0, total: 1000` (100% quota remaining in `/api/usage/provider-limits`). It has never chatted a single token.
- **The Cause**: The account is actually stuck on Google Cloud Code's security validation (`VALIDATION_REQUIRED` 403). OmniRoute failed earlier, cooling it down locally, so OmniRoute refuses to even contact Google upstream and replies with a local rate-limit cooldown message.

---

## 9. Antigravity Pro VMware Rescue Pipeline (`antigravity_rescue`)

When Google Cloud Code sets the account-level `403 VALIDATION_REQUIRED` flag, standard OAuth web re-auth in GPM or browser does **NOT** clear it because Google binds the challenge to device fingerprint + proxy IP history.

### Recovery Workflow Architecture (`D:\Taadaa\GPM auto\scripts\antigravity_rescue`)

1. **Only Rescue Pro Accounts**:
   Check `providerSpecificData.tier == "g1-pro-tier"` in OmniRoute before spending phone-scan effort. Standard/free tier accounts are not worth it.
2. **Dedicated VMware Virtual Machine**:
   - VM Path: `D:\VM\ag-onboard\ag-onboard.vmx`
   - Canonical snapshot: `baseline-v2.17` (Antigravity 2.17.0 installed, Chrome AG as OS default, kit at `C:\ag-kit`, guest account `tada` / `Ag123456`).
3. **Exact S7 1:1 Mobile Proxy TUN**:
   - Resolve the account's assigned mobile proxy from `master_gmail_manager.xlsx` (column 10/11: `test.taadaa.click:<port>`).
   - Start sing-box TUN inside the VM so 100% of the VM's egress traffic routes through that exact mobile IP.
4. **Real Antigravity Desktop App Execution**:
   - Launch the real Electron desktop client (`Antigravity.exe`) inside the VM under interactive Session 1 (`-interactive`). Desktop icon is located at (X=38, Y=459).
   - Sign in with Google as `<email>` inside the VM.
5. **Google QR Code Challenge Resolution**:
   - Trigger a chat request. Antigravity displays `Error Verification Required`.
   - Click `Complete verification` -> Chrome AG opens `accounts.google.com/...` with **"Xác minh thông tin để tiếp tục"** and an official Google QR code.
   - Scan the QR code using a **real physical phone's native Camera app** (NOT Zalo, which fails silently on this specific Google challenge).
6. **Isolated Live Verification**:
   - Run `python verify_and_finalize.py <email>`:
     - Disables all other active connections in OmniRoute.
     - Tests the rescued account in complete isolation (preventing OmniRoute silent fallback to another account).
     - Upon HTTP 200, re-enables the account and snapshots the VM as `<local-part>-verified`.

### VMware Workstation Automation Pitfalls

| Pitfall | Cause | Recovery / Prevention |
|---|---|---|
| `captureScreen` vs `captureScreenInGuest` | `vmrun` command syntax error. | Use `vmrun -T ws -gu tada -gp Ag123456 captureScreen <vmx> <host_dest_path>`. |
| Black screen capture (5KB image) | (a) VMware modal dialog on host (e.g. `Software Updates`) pauses the VM; or (b) Guest Windows display sleeps after ~10m idle. | (a) Unpause VM with `vmrun unpause <vmx>` and dismiss host dialogs via `computer_use`; (b) Wake guest display by running an interactive PowerShell script that sends mouse click + `{ESC}`. Normal awake screenshot is ~180KB+. |
| Antigravity launches in Session 0 | `vmrun runProgramInGuest` runs in background Session 0 by default. | Must always supply `-interactive` to `vmrun runProgramInGuest` so UI windows appear on the visible desktop in Session 1. |
| `subprocess.run` hang on `vmrun` | VMware child processes leave pipe open when using `capture_output=True`. | Discard stdout/stderr using `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL` with a strict timeout (150s). |


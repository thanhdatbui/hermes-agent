# False Full Quota Illusion, Stale Grant Pitfall & Antigravity OAuth Warning Bypass

## 1. The "100% Full Quota" Dashboard Illusion vs Upstream 403 / project_route_error

### Symptom
- OmniRoute / 9Router web dashboard shows a green indicator:
  - `Antigravity • Pro`
  - `Token expires in 0h 53m`
  - `Gemini 3.1 Flash Lite: 100% left`
  - `Claude Opus 4 6 Thinking: 100% left`
  - `Claude Sonnet 4 6: 100% left`
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
1. **Local Quota Accounting**: OmniRoute/9Router UI calculates "100% left" by measuring tokens consumed in `call_logs` against plan limit. If an account is newly provisioned or has 0 successful calls, it calculates 0 usage -> displays 100% remaining regardless of whether the OAuth credentials are alive or dead!
2. **Local Token Expiry Calculation**: "Token expires in Xm" is calculated against `token_expires_at` column in SQLite `provider_connections`, not a live heartbeat to Google.
3. **Stale Refresh Token (`invalid_grant`)**: When an account was activated on Google One Pro, but the coordinator copied an old connection ID or token from 1+ months ago without running fresh OAuth:
   - Google Cloud Code rejects expired access token with 401.
   - OmniRoute calls `https://oauth2.googleapis.com/token` to refresh.
   - Google rejects refresh token with `HTTP 400: {"error": "invalid_grant", "error_description": "Bad Request"}`.
   - OmniRoute classifies upstream 401/403 as `project_route_error`.
   - AGY CLI throws the dead account into a 30m-2h 429 cooldown.

### Diagnostic Rule
- **NEVER trust dashboard 100% quota bar** when investigating failures.
- Check SQLite `provider_connections`:
  ```sql
  SELECT id, email, created_at, updated_at, token_expires_at, last_error_type
  FROM provider_connections WHERE email = '...';
  ```
- Test Google refresh token directly via Python/curl to check for `invalid_grant`.

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

### Deterministic Recovery Workflow
1. Extract `validation_url` from `omniroute-stdout.log`.
2. Connect to the account's GPM profile via Playwright CDP (`skip_proxy_check=true`).
3. Navigate directly to `validation_url`.
4. Page shows: *"Phiên của bạn đã kết thúc vì không có hoạt động. Hãy thử đăng nhập lại"*.
5. The button element is `<button>` with text **`Thử lại`** (or `Đăng nhập lại`).
6. Click the button -> Google validates the session and immediately redirects to `https://developers.google.com/gemini-code-assist/auth/auth_success_gemini` (*"Xác thực thành công | Gemini Code Assist | Google for Developers"*).
7. `VALIDATION_REQUIRED` flag is lifted instantly on Google upstream. The account resumes serving requests without token re-minting.

---

## 7. Google One AI Pro Link Activation Pitfalls & Schema Contracts

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

### OmniRoute `proxy_assignments` SQLite Schema Contract
- Table: `proxy_assignments`
  - `id`: **INTEGER PRIMARY KEY AUTOINCREMENT** (Do NOT pass string UUID into `id`, or SQLite throws `IntegrityError: datatype mismatch`).
  - `proxy_id`: TEXT UUID from `proxy_registry`.
  - `scope`: `'connection'` (or `'provider'`).
  - `scope_id`: TEXT UUID of the connection in `provider_connections`.
  - `position`: `0`.
- Safe SQL:
  ```sql
  DELETE FROM proxy_assignments WHERE scope_id = '<CONN_ID>';
  INSERT INTO proxy_assignments (proxy_id, scope, scope_id, position, created_at, updated_at) 
  VALUES ('<PROXY_ID>', 'connection', '<CONN_ID>', 0, datetime('now'), datetime('now'));
  ```


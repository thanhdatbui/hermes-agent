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

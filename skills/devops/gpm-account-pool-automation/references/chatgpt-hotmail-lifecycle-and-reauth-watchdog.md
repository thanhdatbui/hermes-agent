# ChatGPT & Hotmail Account Lifecycle, Dual-Channel OTP, and Re-Auth Watchdog

## 1. Context & Motivation
When ChatGPT Web or Codex accounts managed on OmniRoute (`:20129`) and 9Router (`:20128`) encounter session invalidation (401, token expired, session revoked), the proxy pools suffer degraded throughput.
However, accounts fall into two fundamentally distinct categories:
1. **Permanently Banned / Deactivated (`account_deactivated`)**: OpenAI has revoked the user ID and disabled access permanently. Entering OTP responds with *"Bạn không có tài khoản vì tài khoản đó đã bị xóa hoặc vô hiệu hóa"*. These MUST be purged immediately and recorded to avoid futile retries.
2. **Dropped Sessions / Unauthenticated**: The account is still alive, but its OAuth token or session cookie expired. Re-logging in on GPM and extracting fresh tokens rescues the account back into the pool.

## 2. Dual-Channel OTP Retrieval Invariant
Hotmail accounts used across the farm do NOT all possess active Microsoft Graph API OAuth tokens:
- **Channel 1 (Graph API - Preferred O(1))**:
  * Applies ONLY to accounts with a valid `refresh_token` and `client_id` in `latest_bought_70.txt` or database.
  * Direct HTTP call to `https://graph.microsoft.com/v1.0/me/messages` extracts the 6-digit OTP in 1–2 seconds without browser overhead.
- **Channel 2 (Outlook Webmail Fallback - Mandatory when no token)**:
  * When Graph API fails (token expired, `invalid_grant`, or account only has password), the automation MUST open the mailbox directly in the GPM browser (`https://outlook.live.com/mail/0/`).
  * **Reuse Canonical Login Code**: CẤM tự chế script đăng nhập Hotmail tạm bợ. BẮT BUỘC tái sử dụng các hàm và selector chuẩn từ `D:/Taadaa/Hotmail/scripts/batch_gpm_hotmail_password_login.py` và `read_otp_gpm.py`:
    - Email/password input: `input[name="loginfmt"]`, `input[name="passwd"]`.
    - Submit buttons: `#idSIButton9`, `input[type="submit"]`.
    - Switch method: `#idA_PWD_SwitchToPassword`, `a:has-text('Use your password instead')`.
    - KMSI bypass: `#declineButton`, `#idSIButton9`.
    - Mail row reading: `[role="row"]`, `[role="option"]`, bóc regex 6 số OTP.

## 3. Persistent Lifecycle State & O(1) Skip
All account states MUST be persisted to `D:/Taadaa/runtime/chatgpt_account_lifecycle.json`:
- Structure:
  ```json
  {
    "email@hotmail.com": {
      "status": "DEAD_DEACTIVATED",
      "updated_at": 1791711204.45,
      "proof": "D:\\Taadaa\\runtime\\artifacts\\deactivated_email.png"
    }
  }
  ```
- **O(1) Skip**: Any account marked `DEAD_DEACTIVATED` must be checked first and skipped immediately in all subsequent runs (both cron and manual audit). Do not start GPM profiles or request OTPs for dead accounts.

## 4. Re-Login & Re-OAuth Flow
1. **Identify Dropped Sessions**: Probe `:20129/api/providers/{id}/test` or catch upstream 401.
2. **Match GPM Profile**: Paginate GPM API (`page=1..10`, `per_page=100`) using substring matching (`email.lower() in profile_name.lower()`).
3. **Login to ChatGPT via CDP**:
   - Navigate to `https://chatgpt.com/auth/login`.
   - Fill email using React native setter (`Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set`).
   - Click submit button with exact text filter: exclude `Google`, `Apple`, `thoại`.
   - On `email-verification`, retrieve OTP via Dual-Channel OTP, fill code, and submit.
4. **Branching**:
   - **Case A: `account_deactivated`**:
     * Capture screenshot proof to `D:/Taadaa/runtime/artifacts/deactivated_<email>.png`.
     * Update state to `DEAD_DEACTIVATED`.
     * Purge from OmniRoute & 9Router: delete connection from SQLite `provider_connections`, clean `combos.data['models']` JSON, and hot-reload `PUT /api/combos/{id}`.
   - **Case B: Successful Login (`New chat` / Live Session)**:
     * Extract `__Secure-next-auth.session-token` via CDP `Network.getCookies`.
     * Sync updated session token into OmniRoute config & SQLite.
     * Update state to `LIVE` (`has_token: true`).
5. **Report Emission**:
   - Always output structured report to `D:/Taadaa/reports/chatgpt_lifecycle_report.json` with counts (total audited, live, dead purged, skipped) and detail records.

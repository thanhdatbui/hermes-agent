# GPM Antidetect & Meta/Instagram Auth Automation Quirks (2026-10)

## 1. GPM Local API Profile Management Quirks
- **Local API Endpoint:** `http://127.0.0.1:19995/api/v3/profiles`
- **Profile Creation Key Constraint:**
  - In `POST /api/v3/profiles/create`, the JSON payload MUST use `'profile_name'` or `'Profile_name'` (e.g. `{"Profile_name": "...", "raw_proxy": "", "group_id": 1}`).
  - Using `'name'` triggers SQLite error: `constraint failed: NOT NULL constraint failed: Profiles.Name`.
- **Proxy Update:**
  - `POST /api/v3/profiles/update/<profile_id>` accepts `{"raw_proxy": "<ip>:<port>[:user:pass]"}`.
  - Do NOT prefix with protocol scheme (`http://` or `socks5://`) inside raw_proxy string for GPM; raw string like `184.75.221.82:3118` or `198.23.243.226:6361:user:pass` is parsed natively by GPM. Passing `http://` causes Chromium launch error `net::ERR_NO_SUPPORTED_PROXIES`.
- **Profile Launch & Stop:**
  - Launch: `POST /api/v3/profiles/start/<profile_id>` with payload `{"win_scale": "0.8"}` returns JSON containing `remote_debugging_address` (e.g. `127.0.0.1:54957`) and `process_id`.
  - When stopping a profile via `/api/v3/profiles/stop/<id>`, Chrome process may linger or remain attached to the port. If a fresh restart is needed, verify PID via `tasklist` and kill leftover instance (`taskkill /F /PID <pid>`) before starting again to avoid stale browser state.

## 2. Playwright Input & Coordinate Traps on Dynamic Forms
- **Invisible / Unattached Input Locators:**
  - React/Next.js dynamic forms (e.g. Meta / Muse AI login inputs) often fail Playwright standard `locator('input[type="text"]').fill(...)` with `Timeout 30000ms exceeded` because elements exist in DOM before bounding layout is finalized or have overlay containers.
  - **Remedy:** Retrieve coordinate via `page.evaluate()` or `locator.bounding_box()`, then click center point `page.mouse.click(x, y)` followed by direct keyboard typing `page.keyboard.type(text, delay=50)` and `page.keyboard.press('Enter')`.

## 3. Meta Checkpoints & Age Verification Workflows
- **Instagram Automated 2FA Login:**
  - Standard clone accounts with 2FA secret: compute TOTP using standard SHA1 base32 RFC6238 (`time.time() // 30`).
  - Submit credentials via `name="email"` and `name="pass"`, then if redirected to `/two_factor` or `/two_step_verification`, locate `input[name="verificationCode"]` and submit TOTP.
- **Meta Checkpoint Rejection ("Bạn hiện không thể tạo tài khoản mới"):**
  - Datacenter IPs / Shared VPN ranges attempting multi-step creation on `muse.ai` / `auth.meta.com` will pass initial OTP but fail at the final submit / DOB confirmation step.
  - Expired OIDC challenge (`code_challenge` / state mismatch) after multiple retries results in `https://muse.ai/oidc/error` ("We couldn't log you in"). Always restart a clean flow with fresh cookies when state is invalidated.

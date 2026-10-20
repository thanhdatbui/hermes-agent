# GPM Login Session Persistence & Canary Verification

## Reliable execution path

For a login or canary that must persist into a GPM profile:

1. Resolve the exact GPM `profile_id` for the target email. Do not infer identity from a folder name alone.
2. Start the profile through the GPM Local API:
   ```text
   GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?skip_proxy_check=true
   ```
3. Read `data.remote_debugging_address` from the response.
4. Connect Playwright with:
   ```python
   browser = playwright.chromium.connect_over_cdp(
       f"http://{remote_debugging_address}"
   )
   ```
   Do not pass a second Playwright proxy; GPM owns the profile proxy.
5. Perform the login through the CDP-connected page/context.
6. Close the CDP connection and stop the profile through:
   ```text
   GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}
   ```
7. Restart the same profile through GPM API/CDP and verify persistence before reporting success.

## False-positive checks

`login_only_success` is session telemetry, not persistence proof. A run that reaches `myaccount.google.com` can still fail to persist when the browser was launched directly with `launch_persistent_context` instead of through GPM lifecycle management.

Reject these as unauthenticated evidence:

- URL containing `/account/about`.
- Body text such as `Đăng nhập vào Tài khoản Google của bạn` or `Sign in to your Google Account`.
- Generic navigation labels such as `Go to your Google Account` or `Truy cập vào Tài khoản Google`.

An account label is useful only when it is account-specific: it should contain the target email or an account-specific label containing an `@` address. Always inspect the body and URL as well; do not accept a single generic aria-label.

## Google 2FA TOTP Form UI Drift & Challenge Disambiguation

In modern Google login flows (particularly Vietnamese `vi-VN` locale):
1. **TOTP Input Field Selector:** Google renders "Ứng dụng Google Authenticator: Nhận mã xác minh..." with an `<input type="tel">` instead of `#totpPin` or `input[name="totpPin"]`.
   - Selector must cover: `input#totpPin, input[name="totpPin"], input[type="tel"]`.
   - **Collision Guard:** You MUST guard against typing the 6-digit TOTP into phone confirmation inputs (`input#phoneNumberId, input[name="phoneNumber"]`). Only treat `input[type="tel"]` as TOTP if phone-number confirmation attributes are absent and the challenge context indicates Authenticator/TOTP.
2. **Recovery Email False-Trigger Isolation:**
   - Broad selectors such as `input[type="email"]:not(#identifierId)` when `challenge` is in the URL will falsely match during a TOTP challenge.
   - Strictly require that `#knowledge-preregistered-email-response` exists in the DOM or the page text contains `"email khôi phục"` before executing recovery email submission.

## Offline Test Suite & IPC Decoupling

1. **Unit Test Fallback for GPM Launchers:**
   - In production, pure login (`--login-only`) resolves GPM profile IDs and connects via CDP.
   - In unit tests with mock profiles (`C:\fake`) and mocked environments, wrap the GPM API resolution/start in a try-except. If `acc` does not specify an explicit `gpm_profile_id` and GPM API fails or is offline, gracefully fall back to `p.chromium.launch_persistent_context` when `prof_dir` is present.
2. **Library Decoupling (`urllib.request` vs `requests`):**
   - If tests mock `requests` to assert that zero external HTTP calls occurred (e.g. asserting `mock_req.get.call_count == 0`), helper calls to GPM Local API via `requests.get` will fail the assertion.
   - Use `urllib.request.urlopen` for internal GPM Local API calls (`gpm_get`) to decouple antidetect IPC from application-level `requests` mocking.

## Canary closeout

Before accepting a GPM code change:

- Run the focused offline tests and syntax check.
- Run the live profile through the GPM API/CDP path.
- Capture the actual post-login screen.
- Inspect the image with vision before attaching it as evidence.
- Restart the same GPM profile and verify the authenticated state again.
- Ensure the canary receipt is fresh, its media exists, its SHA-256 matches, and its scope/diff matches the current change.
- If restart verification returns the Google landing page, mark the task BLOCKED; do not convert the in-session telemetry into `DONE`.

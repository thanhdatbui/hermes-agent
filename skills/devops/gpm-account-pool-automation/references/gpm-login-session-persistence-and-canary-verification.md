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

## Canary closeout

Before accepting a GPM code change:

- Run the focused offline tests and syntax check.
- Run the live profile through the GPM API/CDP path.
- Capture the actual post-login screen.
- Inspect the image with vision before attaching it as evidence.
- Restart the same GPM profile and verify the authenticated state again.
- Ensure the canary receipt is fresh, its media exists, its SHA-256 matches, and its scope/diff matches the current change.
- If restart verification returns the Google landing page, mark the task BLOCKED; do not convert the in-session telemetry into `DONE`.

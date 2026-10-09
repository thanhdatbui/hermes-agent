# ChatGPT live-check via GPM API + Playwright/CDP

Reusable read-only verification pattern for an exact GPM profile.

## Safe sequence
1. Resolve the exact profile by both profile ID and expected account/name before starting.
2. Call `GET /api/v3/profiles/start/{id}` exactly once. If the API explicitly reports an existing/running owner, fail closed: do not attach, navigate, or stop.
3. Connect to the returned `remote_debugging_address` with Playwright `connect_over_cdp`.
4. Enumerate all pages. GPM may expose an extension/offscreen page first (for example a MetaMask `chrome-extension://.../offscreen.html` target) with a zero-sized viewport. Prefer an existing `http://`/`https://` page; otherwise create a normal page.
5. Set a bounded viewport before screenshot (`1365x900` is a practical default), then navigate only to `https://chatgpt.com/` with `wait_until="commit"` and a bounded timeout. Do not click login, account picker, SSO, OAuth, or onboarding controls for a live check.
6. Read `page.url`, title, and `body.inner_text()`. Capture the screenshot before any teardown.
7. Run Windows-native WinRT OCR against the exact fresh screenshot. Tesseract is not required; use the installed `windows-native-ocr` helper or its PowerShell implementation.
8. Stop only if this run successfully started the profile. Record the complete start and stop JSON responses and the physical screenshot path.

## Evidence gates
- A ChatGPT URL or prompt box alone does not prove authentication. Guest state is confirmed when visible text/OCR contains login/sign-up controls, or an account-picker/guest surface.
- A screenshot failure caused by a zero-width extension target means the target selection was wrong, not that ChatGPT is unavailable. Re-select a web page and set a viewport before retrying.
- `browser.close()`/CDP disconnect is not the GPM lifecycle stop. The GPM stop API response must be recorded separately.
- Screenshot and OCR must be timestamped/fresh and captured before stop. Never report success from API status alone.

## Report fields
`profile_id`, expected account, exact URL, title, visible text, OCR text, screenshot path/existence, start response, stop response, whether stop was performed, and any race/lock evidence.

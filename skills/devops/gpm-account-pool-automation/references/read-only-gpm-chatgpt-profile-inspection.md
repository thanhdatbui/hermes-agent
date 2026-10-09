# Read-only sequential GPM + ChatGPT Web inspection

Use this for an operator request to inspect exact GPM profiles without logging in, selecting an account, OAuth/SSO, or purchasing phone verification.

## Canonical sequence

1. Resolve each target to the exact GPM profile ID before starting. Do not use name substring matching when an ID is available.
2. Process targets strictly one at a time: `start -> fresh browser-open screenshot/text -> navigate to chatgpt.com if needed -> fresh screenshot/text -> stop`. Do not start target 2 until target 1's stop response is confirmed.
3. Start/stop through GPM Local API v3 (`127.0.0.1:19995`), and connect to the returned `remote_debugging_address` over CDP.
4. Immediately after CDP attach, enumerate pages. GPM/Chromium may expose an extension `chrome-extension://.../offscreen.html` page first; prefer a non-extension, non-devtools page. If no real page exists, create a new page rather than treating an extension offscreen page as the browser surface.
5. Capture the browser-open state before navigation. Then navigate to `https://chatgpt.com/` and capture again, even if the profile was already there.
6. Never click `Login`, `Sign up`, account-picker entries, Google SSO, OAuth, challenge controls, or phone-purchase UI during an inspection.
7. Stop the exact profile in `finally`, after the final screenshot attempt. Persist the API responses and physical screenshot paths.

## Evidence classification

- **Guest / not authenticated:** visible `Login/Đăng nhập` or `Sign up/Đăng ký` remains; a chat composer alone is not proof of login.
- **Account picker / candidate session, not verified login:** the target email/name is visible in `Welcome back / Chào mừng trở lại / Choose an account`, but Login/Sign up remains or the picker has not been selected. Report as unconfirmed; do not select it merely to prove state.
- **Authenticated account:** only claim this when Login/Sign up controls are absent and a profile artifact (name/avatar/account menu or equivalent) is visible.
- **Challenge/Sentinel:** report only when fresh visible text or screenshot actually shows it. Do not infer it from a URL, timeout, or profile metadata.
- **Insufficient evidence:** screenshot fails, page is an extension offscreen page, or visible text cannot be read. Preserve the exact error and do not substitute a different page/screenshot.

## Operational pitfall

A successful `start` API response does not guarantee the first CDP page is a visible browser tab. Extension offscreen pages can have zero width and cause `Page.screenshot` to fail. Page selection is part of evidence correctness, not a cosmetic workaround.

See also the evidence-first rules in `ui-evidence-first`, especially the negative auth gate and capture-before-teardown rule.
# Manual Products Checklive Automation (Shopclone7 / Doravo)

## Scope & Inventory Context
- Manual products: `products.supplier_id = 0` (or `NULL`), inventory rows stored in `product_stock` (`uid`, `account`, `product_code`).
- Live active inventory with stock (2026-08-19):
  - **SP 40 (`TikTok Random Live`)**: stock format `username|password|cookie...`, `uid` = username (e.g. `sonaairhrk395682`).
  - **SP 57 (`Instagram 2FA On`)**: stock format `username|password|2fa...`, `uid` = username (e.g. `thalamus725`).
- Dead account lifecycle:
  - Account verified DEAD/banned must be inserted into `product_die` and removed from `product_stock` within a DB transaction (`START TRANSACTION` ... `COMMIT`).
  - Account verified LIVE: update `time_check_live = UNIX_TIMESTAMP()`.

## Web-Based External Checklive Automation Findings

### 1. `clonefbig.com/checklive` (Instagram Checklive)
- **Input format**: plain `username` (one per line, e.g. `thalamus725` or `@thalamus725`). Never pass passwords or 2FA keys.
- **Protection**: Cloudflare Turnstile CAPTCHA (`0x4AAAAAADmbPJb7_INQvhB_`) required for WebSocket payload (`cf_token`).
- **Headless Automation Recipe (Playwright)**:
  - Launch with `args=['--disable-blink-features=AutomationControlled']` and realistic User-Agent.
  - Navigate to `https://clonefbig.com/checklive` (`domcontentloaded`).
  - Poll for `input[name="cf-turnstile-response"]` value (Cloudflare Turnstile auto-resolves within 1-3s in non-automated Chrome context).
  - Fill `#inputArea` with newline-separated usernames.
  - Trigger `startCheck()` via `page.evaluate('startCheck()')`.
  - Poll `#liveOutput`, `#dieOutput`, `#liveCount`, `#dieCount` until complete.
  - Verified 2026-08-19: parses Live vs Die in ~4s.

### 2. `khommo247.com/cong-cu/check-tiktok` (TikTok Checklive)
- **Input format**: `#ttList` textarea takes usernames.
- **Protection & Gate**:
  - Cloudflare Managed Challenge on initial request (auto-clears in browser context after 3-5s).
  - **Login Gate**: Clicking `#ttBtnStart` triggers `toolShowLoginGate()`, showing modal `#toolLoginGate` ("Yêu cầu đăng nhập"). Requires logged-in session / cookies on khommo247.
- **Alternative for TikTok**: Use the repository's built-in GitHub Actions workflow (`thanhdatbui/tiktok_check_live`, `tiktok-checklive.yml` with Playwright Chromium `check_live.js`) configured in `settings` (`tiktok_checklive_github_*`), which runs headless without third-party web account dependency.

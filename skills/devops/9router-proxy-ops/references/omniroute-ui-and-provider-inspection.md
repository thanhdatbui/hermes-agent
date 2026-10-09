# OmniRoute Web UI & Provider Inspection

OmniRoute Web UI operates on `http://127.0.0.1:20129`.

## 1. Web UI URL Routes
- **Dashboard Overview:** `http://127.0.0.1:20129/dashboard` (root `/` auto-redirects here).
- **Providers Directory:** `http://127.0.0.1:20129/dashboard/providers`
- **Direct Provider Details:** `http://127.0.0.1:20129/dashboard/providers/<provider_id>`
  - E.g. `/dashboard/providers/antigravity` for Google Antigravity account pool.
  - E.g. `/dashboard/providers/opencode` for OpenCode connections.
  - E.g. `/dashboard/providers/openrouter` for OpenRouter configuration.
- **API Key Management:** `http://127.0.0.1:20129/dashboard/api-manager`
- **Request Logs:** `http://127.0.0.1:20129/dashboard/logs`
- **Analytics:** `http://127.0.0.1:20129/dashboard/analytics`

## 2. Provider Account Inspection & Masking
- **Default Email Masking:** The UI intentionally masks account email addresses for privacy (e.g., `dok***********@******com`, `pha**************@******com`).
- **Account Verification:**
  - Verify account presence via index `#N` (e.g. `#1` to `#42`), connection status badges (`đã kết nối` / `connected`), and attached proxy tags (e.g. `test.taadaa.click`, `mirotik_10009`).
  - To view unmasked account credentials or tokens programmatically, inspect `~/.omniroute/storage.sqlite` directly rather than scraping DOM text.

## 3. Headless Browser / Inspection Tooling
- **Built-in `browser_navigate`:** Use Hermes built-in `browser_navigate`, `browser_snapshot`, and `browser_console` to inspect OmniRoute pages. It connects directly to `127.0.0.1:20129` without needing external browser installs.
- **Playwright Pitfall on Host:** System Python environment may have `playwright` package installed but lacks pre-downloaded chromium headless binaries (`ms-playwright`). Do not attempt CLI playwright scripts without verifying binaries or use `browser_navigate` directly.

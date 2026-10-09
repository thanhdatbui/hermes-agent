# Cockpit Codex OAuth reauthorization — evidence-bound workflow

Use this reference when a Cockpit Codex OAuth account shows `401`, `token_revoked`, `auth_unavailable`, or when reauthorizing a Free account through a GPM profile.

## Ground truth from the investigated flow

- Cockpit's local sidecar can expose an OpenAI-compatible endpoint (commonly `http://127.0.0.1:60818/v1`). `GET /v1/models` is only an advertised-model list; it does **not** prove the selected account is authorized for every advertised model.
- **Model Namespace & Ground Truth Matrix**:
  - Dòng 6.1 không tồn tại trong backend OpenAI Codex hay binary `cockpit-cliproxy.exe` (không có `gpt-6.1*` hay `gpt-6-terra`).
  - Dòng GPT-6 gồm: `gpt-6-luna` (Lightweight), `gpt-6-sol` (Flagship), `gpt-6-astra` (Reasoning).
  - Dòng GPT-5.6 gồm: `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`.
  - **Free Account Entitlement**: Upstream OpenAI chặn cứng (`400/503: The model is not supported when using Codex with a ChatGPT account`) đối với các model flagship (`gpt-6-sol`, `gpt-5.6-sol`, `gpt-6-astra`). Tài khoản Free CHỈ gọi được: `gpt-6-luna`, `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.5`, `codex-auto-review`.
- A model label such as `sol 6.1` is not interchangeable with a provider model ID. Test the exact ID returned by `/v1/models` (for example `gpt-6-sol` or `gpt-5.6-sol`) and record the literal response. An unknown alias can correctly return `404 model_not_available`.
- A `200` request from an earlier account/session is historical evidence only. A current `token_revoked` state must be repaired with a fresh OAuth transaction, not by reusing or decrypting an old refresh token.
- **Tự động trích xuất OTP qua Hotmail Microsoft Graph API**: Khi tài khoản có sẵn `refresh_token` và `client_id` (trong `D:/Taadaa/Hotmail/`), không cần bắt user nhập tay mã email verification. Dùng refresh token đổi `access_token` tại `https://login.microsoftonline.com/common/oauth2/v2.0/token` (qua đúng proxy của profile) rồi đọc inbox `https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages` để lấy OTP 6 số mới nhất từ `noreply@tm.openai.com` / `noreply@tm1.openai.com` và tự động điền vào CDP Playwright.

## Safe single-account sequence

1. Select exactly one target account and its matching GPM profile/proxy. Do not batch OAuth transactions.
2. In Cockpit, generate a **fresh** OAuth URL/state. Never reuse an old authorization link or callback; the callback listener/state is single-flight (often `localhost:1455`).
3. Start the intended GPM profile with the proxy already bound; verify its CDP address and the browser page before navigating. Do not silently switch to another profile or another account.
4. Open the fresh OAuth URL in that profile and capture a screenshot immediately after each state-changing action. The expected pre-auth states include OpenAI login and, for passwordless/email flow, an email-verification screen.
5. If OpenAI requests an email verification code:
   - **Hotmail with Graph API token available** (in `D:/Taadaa/Hotmail/`): **BẮT BUỘC TỰ ĐỘNG LẤY VÀ NHẬP**, CẤM dừng lại bắt user nhập tay. Dùng refresh token đổi `access_token` qua endpoint `https://login.microsoftonline.com/common/oauth2/v2.0/token` (bọc proxy của profile), query inbox `https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages`, trích xuất regex 6 chữ số (`\b\d{6}\b`) từ mail gửi bởi `noreply@tm.openai.com` / `noreply@tm1.openai.com`, và điền trực tiếp vào input field qua Playwright CDP rồi submit.
   - **Tài khoản không có token Graph API**: Chỉ khi này mới dừng lại tại ô nhập mã và nhờ user nhập giúp. Sau khi submit, chụp ảnh kiểm chứng post-submit.
6. Wait for Cockpit's own success/import state. Do not treat `Open in Browser`, a generated URL, or an email-verification screen as successful import.
7. Re-read Cockpit account storage and sidecar/manifest state. Verify the exact email/account ID, plan state, proxy binding, and absence of `token_revoked`/`auth_unavailable`.
8. Call `/v1/models`, then make one minimal mocked-safe/low-cost request using the exact intended model ID. Read the resulting Cockpit request log and verify account email, requested model, upstream model, HTTP status, and token counts. Only then report OAuth success.
9. If the result is `401 token_revoked`, `503 auth_unavailable`, or the account enters model cooldown, stop the account flow, preserve the account, and start a new OAuth state. Do not loop blindly.

## Evidence contract

For each account, retain:

- fresh OAuth URL/state generation time (redacted URL; never publish auth codes);
- GPM profile ID, CDP endpoint, and proxy label (redact proxy credentials);
- pre-auth and post-auth screenshots with timestamps;
- Cockpit account-store/manifest readback with secrets removed;
- `/v1/models` response and one minimal request result;
- request-log row showing requested versus upstream model and account identity.

Classify the result as `IMPORTED_AND_TESTED`, `WAITING_FOR_USER_OTP`, `TOKEN_REVOKED`, `MODEL_NOT_AVAILABLE`, or `UNPROVEN`. A generated URL or a browser navigation alone is never `IMPORTED_AND_TESTED`.

## Pitfalls

- Do not infer that a Free account can use a flagship model merely because Cockpit lists the model or accepts the request schema; entitlement and upstream execution require a fresh successful request tied to the account.
- Do not use a stale refresh token as a substitute for OAuth reauthorization.
- Khi làm việc với Hotmail pool đã có Microsoft Graph refresh token, ưu tiên tự động query inbox lấy OTP thay vì dừng lại bắt user nhập tay.
- Do not run multiple Cockpit OAuth flows concurrently; callback/state collisions can bind the wrong account or time out.
- Do not publish API keys, OAuth URLs containing live state, refresh tokens, proxy credentials, or decrypted account blobs in a report.
- COCKPIT MINIMIZE = PORT 1455 DEAD: Nếu cửa sổ Cockpit Tools bị minimize hoặc trôi ngoài màn hình (bounds âm), `localhost:1455` có thể từ chối kết nối (WinError 10061). Luôn kiểm tra `netstat -ano | grep 1455` trước khi chạy auth script; nếu không thấy LISTENING thì Restore cửa sổ hoặc restart Cockpit trước.
- PRE-SCREEN COOKIE TRƯỚC KHI CHẠY OAuth: Trước khi start GPM profile và lấy OAuth URL, đọc cookie qua CDP để xác nhận profile có `unified_session_manifest` hoặc `__Secure-next-auth.session-token`. Profile không có cookies này sẽ đưa người dùng về màn hình đăng nhập mới, tốn thời gian chờ và gây thất bại callback.
- PLAYWRIGHT/CDP AUTH TIMEOUT 55s: Nếu dùng subprocess/terminal để chạy async Playwright, set `timeout >= 100s` trong terminal (background=True) hoặc chạy từng profile riêng lẻ. Script đặt trong vòng lặp với nhiều profile dễ bị exit 124 (timeout) trước khi callback xong.
- AUTH LINK TIMED OUT TRONG COCKPIT: Nếu Cockpit dialog báo "Authentication timed out" (auth link cũ không còn active), phải bấm "Refresh Auth Link" để lấy state mới, KHÔNG được dùng lại URL cũ dù URL chưa thay đổi về mặt ký tự.

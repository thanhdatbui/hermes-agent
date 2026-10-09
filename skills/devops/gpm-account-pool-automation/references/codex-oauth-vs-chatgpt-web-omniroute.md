# Phân biệt OpenAI Codex OAuth vs ChatGPT-Web trên OmniRoute (Port 20129)

## 1. Bản chất hai Provider trên OmniRoute
Khi tích hợp tài khoản ChatGPT từ GPM profile vào OmniRoute (port `20129`), có 2 provider khác nhau:

| Tiêu chí | `codex` (OpenAI Codex OAuth) | `chatgpt-web` (Web Session Cookie) |
| :--- | :--- | :--- |
| **Giao thức** | OAuth 2.0 chuẩn cho CLI (Codex API) | Giả lập Web UI Chat qua SSE cookie |
| **Upstream endpoint** | `https://chatgpt.com/backend-api/codex/responses` | `https://chatgpt.com/backend-api/conversation` |
| **Token nạp** | OAuth Bearer JWT (`accessToken` do Auth0 cấp) | Cookie `__Secure-next-auth.session-token` |
| **Endpoint nạp** | `POST /api/oauth/codex/import-token` | `POST /api/providers` (provider: `chatgpt-web`) |
| **Độ ổn định** | Cao, không bị Cloudflare / Sentinel challenge | Dễ dính Cloudflare 403, Proof-of-Work Sentinel |

---

## 2. Bí quyết vượt bước verify số điện thoại / Device Code của Codex OAuth
- **Vấn đề**: Khi mở link đăng nhập mới của Codex CLI (`https://auth.openai.com/oauth/authorize`), OpenAI Auth0 thường yêu cầu xác minh số điện thoại (OTP/SMS) hoặc challenge thiết bị.
- **Giải pháp**: 
  1. Cho profile GPM đăng nhập sẵn vào `chatgpt.com` thông qua Google OAuth (đã trust phiên Google trên thiết bị).
  2. Dùng Playwright CDP mở URL nội bộ: `https://chatgpt.com/api/auth/session`.
  3. Bóc tách JSON trong thẻ `<pre>` để lấy trường `accessToken` (OAuth JWT hợp lệ với issuer `https://auth.openai.com`, audience `https://api.openai.com/v1`).
  4. Đẩy thẳng token này vào OmniRoute qua `POST http://127.0.0.1:20129/api/oauth/codex/import-token` với payload `{"accessToken": token, "name": label}`.
  5. Bỏ qua được 100% bước kẹt màn hình hỏi số điện thoại / OTP của link authorize rời.

---

## 3. Khả năng hỗ trợ Model của tài khoản ChatGPT trên Codex
- **`gpt-5.6-sol` (bản chuẩn / full reasoning)**: **400 Bad Request**
  `{"detail": "The 'gpt-5.6-sol' model is not supported when using Codex with a ChatGPT account."}`
  *(OpenAI giới hạn chỉ dành riêng cho tài khoản trả phí Codex API Key / Enterprise).*
- **`gpt-5.6-sol-instant`**: **200 OK** (Dùng mượt, phản hồi nhanh, được mở cho tài khoản ChatGPT).
- **`gpt-5.5`**: **200 OK** (Full responses backend, code thông minh nhất hiện tại của Codex).
- **`gpt-5.3-codex-spark`**: **400 Bad Request** (Chỉ dành cho Enterprise/API key).

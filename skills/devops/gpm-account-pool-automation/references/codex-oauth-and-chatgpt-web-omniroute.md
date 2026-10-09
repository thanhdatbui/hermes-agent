# Codex OAuth vs ChatGPT Web Hook on OmniRoute (Port 20129)

## 1. Phân biệt Codex OAuth vs ChatGPT Web
- **`codex` (OpenAI Codex OAuth)**:
  - Bản chất: Chuẩn OAuth 2.0 API chính thức cho developer/CLI (`backend-api/codex/responses`).
  - Model hỗ trợ: `gpt-5.6-terra` (kèm các mức reasoning low/medium/high), `gpt-5.6-luna`, `gpt-5.6-sol-instant`. Lưu ý: `gpt-5.6-sol` bị OpenAI chặn với lỗi 400 trên tài khoản ChatGPT thông thường (chỉ cấp cho Enterprise/Paid Codex API).
  - Ưu điểm: Hỗ trợ Native tool calling, JSON schema, không bị dính Sentinel bot-check hay Cloudflare PoW challenge.
- **`chatgpt-web` (Web Cookie Session)**:
  - Bản chất: Giả lập phiên web UI qua cookie `__Secure-next-auth.session-token` (hỗ trợ cả dạng chunk `.0`, `.1`).
  - Model hỗ trợ: `chatgpt-web/gpt-5.6-luna-free`.
  - Quota: Dùng hạn mức chat web Free thông thường. Dễ bị Cloudflare 403 / Sentinel nếu IP bị nghi ngờ.

## 2. Thủ thuật Bypass OTP/Số điện thoại khi OAuth Codex
- Thay vì mở link authorize từ con số 0 (`auth.openai.com/oauth/authorize`) dễ bị hỏi xác minh số điện thoại hoặc mã OTP:
  1. Cho profile GPMLogin đăng nhập sẵn vào `chatgpt.com` bằng Google OAuth (đã trust phiên trình duyệt).
  2. Dùng CDP Playwright mở `https://chatgpt.com/api/auth/session` để lấy trực tiếp OAuth JWT `accessToken` (do Auth0 cấp).
  3. Bắn POST token vào OmniRoute qua `http://127.0.0.1:20129/api/oauth/codex/import-token` với payload `{"accessToken": token, "name": label}`.

## 3. Cách xem Quota tài khoản Free trên Codex
- Endpoint tra cứu chính xác của OpenAI: `GET https://chatgpt.com/backend-api/wham/usage` với header `Authorization: Bearer <accessToken>`.
- Trả về chi tiết `rate_limit.primary_window.used_percent`, `reset_after_seconds`, `plan_type: "free"`.
- Trên OmniRoute, có thể đọc cache qua `GET http://127.0.0.1:20129/api/usage/provider-limits`. Lưu ý: `import-token` mặc định lưu `authType: "access_token"`, không đổi cứng sang `"oauth"` nếu thiếu `refreshToken` kẻo bị `tokenHealthCheck` gắn cờ `expired`.

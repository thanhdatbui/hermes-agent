# OpenAI Codex & ChatGPT Web Integration, Reasoning Tiers and Quota Tracking on OmniRoute (:20129)

## 1. Bản chất: `codex` (OAuth JWT) vs `chatgpt-web` (Session Cookie)
- **`codex`**: Sử dụng endpoint `POST /api/oauth/codex/import-token` với OAuth JWT `accessToken` từ `https://chatgpt.com/api/auth/session`. Gọi trực tiếp backend API `https://chatgpt.com/backend-api/codex/responses`. Hỗ trợ chuẩn tool calling, native streaming, không bị dính Sentinel bot-check hay Cloudflare PoW challenge.
- **`chatgpt-web`**: Sử dụng cookie `__Secure-next-auth.session-token` (hoặc cookie chunked `.0`, `.1`). Gọi giả lập web UI `/backend-api/conversation`. Dễ bị 403 Cloudflare / Sentinel challenge khi xoay proxy.

## 2. Phân cấp Model GPT-5.6 & Cấp độ Reasoning (Thinking Effort)
- **`gpt-5.6-sol` (Full Thinking)**: Bị OpenAI chặn đối với ChatGPT Free/Plus account (`400 Bad Request`). Chỉ nhận API Key doanh nghiệp trả phí.
- **`gpt-5.6-sol-instant`**: Hoạt động được trên account Free, nhưng bị **tắt hoàn toàn suy nghĩ (`effort = null`)**. Tốc độ phản hồi tức thì (<1s), tuy nhiên dễ bị ảo giác / sai logic trên code phức tạp.
- **`gpt-5.6-terra-*`**: Hỗ trợ đầy đủ cho tài khoản Free qua Codex OAuth với mọi mức effort (`low`, `medium`, `high`, `xhigh`, `max`, `ultra`).
- **Lựa chọn Effort cho Reviewer**:
  - Dùng **`gpt-5.6-terra-high`** (Sweet Spot): Thời gian phản hồi 15–20s, phân tích AST và logic bug chính xác, không bị dính bẫy **Over-thinking / Nitpicking** của mức `max`/`ultra` (mức max kéo dài 45–90s và dễ timeout/bắt bẻ tiểu tiết vô bổ).

## 3. Tra cứu Quota tài khoản Free
Tài khoản Codex Free trên OmniRoute lưu dưới dạng `authType: "access_token"`, do đó web UI OmniRoute mặc định không hiện bảng hạn mức. Tuy nhiên, API nội bộ của OpenAI luôn cấp quota:
- **Endpoint**: `GET https://chatgpt.com/backend-api/wham/usage` (header `Authorization: Bearer <accessToken>`).
- **Dữ liệu**: `rate_limit.primary_window.used_percent` thể hiện % quota đã dùng trong chu kỳ rolling window (~30 ngày).

## 4. Invariants khi viết Hook & Runner GPM vào OmniRoute
1. **Quản lý vòng đời GPM Profile chống rò rỉ RAM**:
   - Khởi tạo `profile_started = False`.
   - Đặt `profile_started = True` ngay khi API `profiles/start` trả về status code `200` (trước khi parse `remote_debugging_address`).
   - Khối `finally:` chỉ gọi `profiles/stop/{profile_id}` nếu `profile_started = True`, và bắt buộc bọc trong `try/except` để tránh exception unhandled trong cleanup che lấp kết quả trả về.
2. **Redact thông tin nhạy cảm**:
   - Sử dụng regex loại bỏ chuỗi JWT `ey...` hoặc token value thành `[REDACTED]` trong mọi error message và log.
3. **Ghim Connection khi Verify**:
   - Khi gửi ping inference test xác thực kết nối vừa import, truyền header `headers={'x-omniroute-connection-id': conn_id}` để OmniRoute định tuyến chính xác vào connection vừa tạo.

# Codex OAuth vs ChatGPT Web Hook & OmniRoute Quota / Model Integration

## 1. Phân biệt cốt lõi giữa `codex` và `chatgpt-web` trên OmniRoute (:20129)

| Tiêu chí | `codex` (OpenAI Codex OAuth) | `chatgpt-web` (Web Session Cookie) |
| :--- | :--- | :--- |
| **Bản chất** | OAuth 2.0 chuẩn cho CLI / Dev (`/api/oauth/codex/import-token`) | Giả lập Web UI qua cookie session (`POST /api/providers`) |
| **Endpoint gọi lên** | `https://chatgpt.com/backend-api/codex/responses` | `https://chatgpt.com/backend-api/conversation` |
| **Loại Token** | OAuth Bearer JWT (`accessToken` lấy từ `/api/auth/session`) | Cookie `__Secure-next-auth.session-token` (hỗ trợ cả `.0`, `.1`) |
| **Model hỗ trợ** | `gpt-5.5`, `gpt-5.6-sol-instant`, `gpt-5.6-terra-*`, `gpt-5.6-luna-*` | `chatgpt-web/gpt-5.6-luna-free` |
| **Độ ổn định** | Cực cao, không bị dính Sentinel / Cloudflare PoW challenge | Dễ bị Cloudflare 403, Sentinel bot-check khi đổi IP |

---

## 2. Bẫy Model 5.6 & Cấp độ Reasoning (Thinking Effort)

### A. Model Sol vs Terra vs Luna
- **`gpt-5.6-sol` (Full Thinking)**: Bị OpenAI khóa đối với tài khoản ChatGPT Free/Plus (`400 Bad Request: The 'gpt-5.6-sol' model is not supported when using Codex with a ChatGPT account`). Chỉ tài khoản Codex API Key trả phí mới gọi được.
- **`gpt-5.6-sol-instant`**: Hoạt động 100%, nhưng bị **tắt hoàn toàn suy nghĩ (`effort = null`)**. Tốc độ phản hồi tức thì (<1s), tuy nhiên dễ bị ảo giác / sai logic trên code khó.
- **`gpt-5.6-terra-*`**: Mở hoàn toàn cho tài khoản Free qua Codex OAuth. Có đầy đủ reasoning (`low`, `medium`, `high`, `xhigh`, `max`, `ultra`).
- **`gpt-5.6-terra-high`**: Điểm ngọt (Sweet spot) cho code review / audit:
  - Phân tích AST và bắt bug logic (như race condition, zero division, off-by-one) cực kỳ chuẩn xác.
  - Thời gian phản hồi 15–20s.
  - Tránh bẫy **Over-thinking / Nitpicking** của mức `max`/`ultra` (mức max thường tốn 45–90s và hay bắt bẻ tiểu tiết vô bổ).

---

## 3. Cách tra cứu Quota của tài khoản Codex Free
Tài khoản Codex Free trên OmniRoute lưu dưới dạng `authType: "access_token"`, do đó giao diện web OmniRoute mặc định không hiện bảng hạn mức. Tuy nhiên, API nội bộ của OpenAI luôn cấp quota:
- **Endpoint**: `GET https://chatgpt.com/backend-api/wham/usage` (với header `Authorization: Bearer <accessToken>`).
- **Dữ liệu trả về**:
  - `plan_type`: `free`
  - `rate_limit.allowed`: `true`
  - `rate_limit.primary_window.used_percent`: % quota đã dùng (rolling window ~30 ngày).

---

## 4. Invariants khi viết Hook & Runner cho GPM Profile vào OmniRoute
1. **Quản lý vòng đời GPM Profile chống rò rỉ RAM**:
   - Biến cờ `profile_started = False`.
   - Bật `profile_started = True` ngay khi HTTP status code của API `profiles/start` là `200` (trước khi kiểm tra `remote_debugging_address`).
   - Khối `finally:` bắt buộc bọc `try/except` khi gọi `profiles/stop/{profile_id}` để tránh unhandled exception trong cleanup che lấp kết quả trả về.
2. **Redact thông tin nhạy cảm**:
   - Tuyệt đối không in raw token hoặc session cookie trong exception message hay log.
   - Sử dụng regex thay thế chuỗi JWT `ey...` hoặc token value thành `[REDACTED]`.
3. **Ghim Connection khi Verify**:
   - Khi gửi ping inference test xác thực kết nối vừa import, bắt buộc truyền header `headers={'x-omniroute-connection-id': conn_id}` để OmniRoute định tuyến chính xác vào connection vừa tạo thay vì round-robin sang connection khác.

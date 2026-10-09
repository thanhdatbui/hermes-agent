# ChatGPT Web & Codex OAuth Batch Automation Patterns on GPM

## 1. Cơ Chế Login ChatGPT & Đồng Bộ Token Vào OmniRoute (Port 20129)

### 1.1 Luồng Tự Động Đăng Nhập ChatGPT Qua Google SSO:
1. **Khởi chạy profile GPM qua Local API v3 (Port 19995):**
   - Gọi `GET http://127.0.0.1:19995/api/v3/profiles/start/{id}?win_scale=0.8`
   - Nhận `remote_debugging_address` (VD: `127.0.0.1:51819`), chờ 2.5 - 3s và kết nối Playwright CDP (`connect_over_cdp`).
2. **Xử lý Cookie Banner & Google SSO:**
   - Điều hướng tới `https://chatgpt.com/auth/login`.
   - Bắt buộc dismiss Cookie Banner (`Chấp nhận tất cả`, `Accept all`) trước khi click nút login.
   - Click `Continue with Google` / `Tiếp tục với Google`.
   - Nếu tab popup Google mở riêng (`accounts.google.com`), switch page sang tab Google, tìm element chứa email và click chọn tài khoản.
   - Xử lý màn hình OAuth Consent (`Tiếp tục` / `Continue` / `Cho phép` / `Allow`).
3. **Xử lý Onboarding Màn Hình Đầu (About You / Age):**
   - Khi redirect về `chatgpt.com`, nếu xuất hiện form hỏi Họ tên / Tuổi:
     - Điền tên vào ô Họ và tên (tự động lấy theo prefix email hoặc tên danh bạ).
     - Điền tuổi (`25`) vào ô `input[name="age"]` hoặc placeholder `tuổi`.
     - Click nút `Tiếp tục` / `Continue`.
   - Kiểm tra vào thành công main chat: body text chứa `Hôm nay bạn muốn làm gì`, `Đoạn chat mới`, hoặc locator `#prompt-textarea`.

### 1.2 Trích Xuất Token Nạp Vào OmniRoute:
- **Provider `chatgpt-web`:**
  - Trích xuất cookie `__Secure-next-auth.session-token` từ context browser (nếu cookie bị chunk thành `.0`, `.1` thì nối theo index).
  - Nạp qua `POST http://127.0.0.1:20129/api/providers` (hoặc `PUT` nếu connection đã tồn tại) với `authType: "apikey"`, `provider: "chatgpt-web"`.
- **Provider `codex`:**
  - Mở URL `https://chatgpt.com/api/auth/session` trên browser.
  - Parse JSON trong thẻ `<pre>` lấy `accessToken` (chuẩn JWT `ey...`, độ dài > 50).
  - Nạp qua `POST http://127.0.0.1:20129/api/oauth/codex/import-token` với `{"accessToken": "...", "name": "..."}`.

---

## 2. Pitfalls & Kỷ Luật Điều Phối Batch (CRITICAL)

1. **Nguy Cơ Batch Timeout Khi Dispatch Worker Gộp Nhiều Profile:**
   - Mỗi profile GPM chạy qua proxy Mobi 4G/MikroTik mất từ 1.5 - 3 phút để khởi động, tải trang Google SSO, redirect ChatGPT và giải quyết onboarding.
   - Gộp 3 profile vào một worker chạy tuần tự dễ chạm trần timeout 600s của subagent (600s / 3 = 200s/acc, nếu gặp proxy lag hoặc trang chờ redirect sẽ bị abort toàn bộ batch).
   - **Kỷ luật:** Khi chạy tự động hóa ChatGPT login cho GPM profile, BẮT BUỘC dispatch **đơn lẻ 1 profile / worker** với timeout tối đa 300s/acc, hoặc runner phải có timeout per-step cực ngắn (<30s/bước) kèm cơ chế fail-fast.

2. **Loopback Proxy & Callback Server Codex (Port 1455):**
   - Nếu nạp Codex qua luồng PKCE `start-callback-server`, OmniRoute mở port local `1455`. Khi profile chạy proxy Mobi 4G, request redirect tới `localhost:1455` sẽ bị proxy chặn.
   - Ưu tiên cơ chế `import-token` trực tiếp qua `POST /api/oauth/codex/import-token` bằng cách đọc `/api/auth/session` trên browser GPM để hoàn toàn không phụ thuộc vào local callback server port 1455.

3. **Kỷ Luật Teardown Profile (Finally Block):**
   - Bất kể thành công, fail-fast hay gặp timeout, khối `finally` BẮT BUỘC gọi `GET /profiles/stop/{id}` để đóng browser và tránh rò rỉ tiến trình Chrome chiếm RAM.

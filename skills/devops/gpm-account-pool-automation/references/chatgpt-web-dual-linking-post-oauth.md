# Tự động liên kết ChatGPT-Web sau khi OAuth Antigravity thành công

Trong pipeline GPM OAuth S7 (`run_oauth_s7_pipeline.py`), sau khi hoàn thành OAuth Antigravity và exchange code lấy connection ID:

## 1. Lý do & Mục tiêu
- **Tận dụng session Google vừa đăng nhập**: GPM browser profile đã lưu sẵn cookie/session Google đăng nhập thành công.
- **Tiết kiệm thao tác thủ công**: Không cần chạy riêng một luồng automation đăng nhập ChatGPT từ đầu.
- **Bổ sung connection vào OmniRoute**: Khai thác thêm model `chatgpt-web/gpt-5.6-sol-high` cho combo `chatgpt-web-pool` phục vụ subagents.

## 2. Quy trình thực hiện (Dual-link flow)
1. **Direct Google OAuth URL**:
   ```
   https://chatgpt.com/auth/login_with?callback_path=%2F&connection=google-oauth2&screen_hint=login_or_signup&ext-web-mobile-direct-social-login=true
   ```
2. **Xử lý Onboarding & Consent**:
   - Vòng lặp kiểm tra URL và DOM (`domcontentloaded`):
     - URL chứa `chatgpt.com` và không có `auth` hay nút Đăng nhập -> thành công.
     - URL chứa `about-you`: tự điền `name` (từ email prefix), `age` (24), bấm submit.
     - Xuất hiện nút `Tiếp tục`, `Continue`, `Cho phép`: click chấp thuận.
     - Xuất hiện `accountchooser`: click chọn email hiện tại.
3. **Trích xuất & Validate Cookie**:
   - Thu thập cookies qua `context.cookies(["https://chatgpt.com"])`.
   - Chuỗi định dạng: `name1=val1; name2=val2; ...`.
   - Kiểm tra điều kiện đủ (> 15 cookies).
   - Gọi OmniRoute API validate:
     ```bash
     POST http://127.0.0.1:20129/api/providers/validate
     {"provider": "chatgpt-web", "apiKey": "<cookie_str>"}
     ```
4. **Nạp Connection & Gán Proxy 1:1**:
   - Nếu valid, tạo connection:
     ```bash
     POST http://127.0.0.1:20129/api/providers/connections
     {"provider": "chatgpt-web", "name": "<email> (GPM Web)", "apiKey": "<cookie_str>", "isActive": true}
     ```
   - Gán proxy 1:1 tương ứng port proxy của profile:
     ```bash
     PUT http://127.0.0.1:20129/api/settings/proxies/assignments
     {"scope": "account", "scopeId": "<conn_id>", "proxyId": "<proxy_id>"}
     ```
5. **Cập nhật Combo Pool trong SQLite Storage**:
   - Mở database OmniRoute: `C:\Users\Kibe\.omniroute\storage.sqlite`.
   - Truy vấn `combos WHERE name='chatgpt-web-pool'`.
   - Append entry model mới với model `chatgpt-web/gpt-5.6-sol-high` và `connectionId`.

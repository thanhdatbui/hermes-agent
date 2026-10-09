# OmniRoute Codex Pool Watchdog & Tri-Provider Health Check

## 1. Kiến trúc Watchdog Pool Healer (`cron_chatgpt_web_pool_watchdog.py`)
Script watchdog chạy định kỳ quét và hồi sinh sức khỏe cho 3 provider chính trên OmniRoute (`:20129`):
1. **ChatGPT-Web**: Direct Google OAuth, Account Chooser, TOTP 2FA, About-you form qua Playwright CDP kết nối GPM profile.
2. **Antigravity**: Tự động mở profile GPM, xác thực Google OAuth consent, exchange refresh token và gán proxy.
3. **Codex**: Kiểm tra trạng thái pool token Codex (`provider == 'codex'`), tự động bật lại toggle bị tắt, phát hiện token chết/hết hạn.

## 2. Quy tắc giám sát Provider Codex
- **Schema OmniRoute SQLite (`C:\Users\Kibe\.omniroute\storage.sqlite`)**:
  - Bảng `provider_connections`.
  - Các trường chính: `id`, `provider`, `name`, `is_active`, `test_status`, `last_error`.
  - Lưu ý: Không có cột `last_test_error`, thông báo lỗi lưu ở `last_error` hoặc truy vấn qua API `:20129/api/providers`.
- **Phục hồi Toggle bị tắt (Accidentally Toggled Off)**:
  - Điều kiện: `testStatus == 'active'` và `isActive == False`.
  - Hành động: Thực hiện SQL direct update `UPDATE provider_connections SET is_active=1 WHERE id=?` mà không cần gọi browser/GPM.
- **Phát hiện Token Broken**:
  - Điều kiện: `testStatus != 'active'`.
  - Ghi nhận vào danh sách `failed_codex` để cảnh báo trong mục `• Cần chú ý (X acc)`.

## 3. Quy chuẩn Báo cáo & Đồng bộ Runtime
- **Định dạng báo cáo**:
  - Tuyệt đối tuân thủ Markdown chuẩn Farm (CẤM dùng raw HTML `<b>`, `<code>`, `<i>`).
  - Định dạng tổng quan:
    ```text
    🤖 [POOL HEALER] BÁO CÁO SỨC KHỎE
    • ChatGPT-Web: X/Y ACTIVE
    • Antigravity: X/Y ACTIVE
    • Codex: X/Y ACTIVE
    ```
  - Silent Watchdog: Nếu không có acc nào được hồi sinh và không có lỗi mới, script giữ im lặng (không in stdout) để tránh spam nhóm Telegram.
- **Đồng bộ Deploy ↔ Runtime**:
  - Source repo: `D:\Taadaa\Hermes\deploy\hermes-home\scripts\cron_chatgpt_web_pool_watchdog.py`
  - Runtime path: `C:\Users\Kibe\AppData\Local\hermes\scripts\cron_chatgpt_web_pool_watchdog.py`
  - Bắt buộc đồng bộ sang runtime path và kiểm tra `python -m py_compile` sau mỗi lần chỉnh sửa.

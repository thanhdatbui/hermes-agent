# OmniRoute Pool Healer Watchdog & GPM OAuth Recovery

## 1. Kiến trúc Watchdog Hồi sinh Pool (`cron_chatgpt_web_pool_watchdog.py`)
- **Tần suất**: Chạy tự động hàng ngày lúc 05:00 AM (cron job `fff7f688990d`), output báo về Telegram group Farm Alert (`-5373649734`).
- **Nhiệm vụ kép**:
  1. Quét ChatGPT-Web (`/api/providers`): lấy session cookie/NextAuth token qua Playwright trên GPM profile, tự động điền credentials từ `gmail_clean_v2.xlsx`, giải TOTP và update cookie vào OmniRoute DB (`storage.sqlite`).
  2. Quét Antigravity OAuth: gọi `/api/oauth/antigravity/authorize`, dùng Playwright kết nối CDP profile GPM, tự động click chọn email / Accept consent, bắt `code` redirect và POST về `/api/oauth/antigravity/exchange`.

## 2. Các nguyên nhân gây lỗi Pool và Hướng xử lý

### A. Lỗi "Không thấy profile GPM" (Tài khoản mồ côi)
- **Triệu chứng**: Watchdog báo `Không thấy profile GPM` (ví dụ `mockieuplus13@gmail.com`, `trieutruc05051997@gmail.com`).
- **Bản chất**: Tài khoản này đã bị xóa/purge khỏi file Excel quản lý (`gmail_clean_v2.xlsx`) hoặc profile GPM đã bị dọn dẹp, nhưng kết nối cũ vẫn còn nằm trong bảng `provider_connections` của OmniRoute SQLite (`C:\Users\Kibe\.omniroute\storage.sqlite`).
- **Xử lý**:
  - Đối chiếu với lịch sử backup purge của Excel (`gmail_clean_v2.bak-purge-*.xlsx`).
  - Nếu tài khoản đã xác nhận DIE và bị purge: xóa bản ghi kết nối khỏi OmniRoute để tránh watchdog báo lỗi lặp lại vô ích:
    ```sql
    DELETE FROM provider_connections WHERE id = '<connection_id>' AND provider = 'antigravity';
    ```

### B. Lỗi "Timeout bắt OAuth code" (35s timeout)
- **Triệu chứng**: GPM profile mở thành công, browser điều hướng tới Google OAuth URL nhưng sau 35s không nhận được callback `/callback?code=...`.
- **Nguyên nhân tiềm ẩn**:
  1. Session Google trong GPM profile bị văng (Google yêu cầu re-login password hoặc giải SMS/phone checkpoint).
  2. Màn hình Google hiển thị trang cảnh báo bảo mật mới, 2-step verification hoặc consent UI đổi selector khiến Playwright locator không click được `Cho phép` / `Tiếp tục`.
  3. Proxy gán vào profile GPM bị chậm/die khiến request tải trang Google Auth vượt quá timeout.
- **Quy trình điều tra & phục hồi**:
  - Không chạy mù toàn bộ pool. Lấy mẫu 1 profile bị timeout mở bằng GPM API (`/profiles/start/{pid}`).
  - Kết nối CDP, inspect DOM/URL thực tế của tab Google Auth.
  - Nếu bị vướng password/2FA: lấy credential từ Excel/backup điền tự động.
  - Nếu selector consent thay đổi: cập nhật thêm selector vào `cron_chatgpt_web_pool_watchdog.py`.
  - Hoàn tất OAuth exchange và đóng profile ngay lập tức.

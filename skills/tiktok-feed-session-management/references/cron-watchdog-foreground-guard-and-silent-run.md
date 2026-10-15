# Cron Watchdog Execution & Foreground Timeout Guard

## Context & Environment Rule
Khi chạy script kiểm tra hoặc watchdog định kỳ (như `feed_session_watchdog.py`, `follow_watchdog.py`) thông qua Hermes `terminal`:
- **Foreground Timeout Guard:** Hệ thống áp dụng guard bắt buộc cho mọi lệnh terminal foreground. Lệnh thiếu tham số `timeout` sẽ bị chặn ngay lập tức với lỗi:
  `[GUARD_FOREGROUND_TIMEOUT_MISSING] Lệnh terminal foreground thiếu timeout! Bắt buộc timeout <= 60s hoặc chạy background=True.`
- Do đó, mọi lệnh gọi chạy script kiểm tra cần chỉ định rõ `timeout: 60` (hoặc `<= 60`).

## Watchdog Idle / Silent Condition
- Khi chạy `feed_session_watchdog.py` trong cron session:
  - Nếu toàn bộ các ca trước đó đã được ghi nhận trong `cron-state/feed_session_reported.json` (hoặc `follow_session_reported.json`).
  - Hoặc ca hiện tại đang trong khung giờ chạy hoặc feed runner / workflow process (`is_feed_runner_active()`) đang active.
  - Script sẽ không in thông báo mới (stdout rỗng).
  - Đối với cron job của Hermes, khi không có nội dung mới cần báo cáo, phản hồi chuẩn là `[SILENT]` để tránh spam người dùng theo đúng chỉ thị.

# Cron Watchdog Execution & Silent Protocol Invariant

## 1. Foreground Terminal Guard vs Watchdog Execution
- **Guard rule:** On Hermes, any foreground terminal call MUST have an explicit `timeout` parameter (`timeout <= 60s`), or it will be rejected with `[GUARD_FOREGROUND_TIMEOUT_MISSING]`.
- **Command:**
  ```bash
  python "D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py"  # With timeout: 30 or 60
  ```
  Or for follow watchdog:
  ```bash
  python "D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py" --mode=follow  # With timeout: 30 or 60
  ```

## 2. Cron Job Silent Contract (`[SILENT]`)
- Khi chạy dưới vai trò cron job:
  - Nếu script không có session mới cần báo cáo (đã report trước đó hoặc phiên chưa kết thúc / chưa có dữ liệu hoàn tất): output stdout của script sẽ rỗng (exit code 0).
  - Khi không có thông tin mới cần chuyển giao cho user / Telegram: Agent BẮT BUỘC phản hồi duy nhất chuỗi `[SILENT]` (tuyệt đối không đính kèm text giải thích hay văn bản thừa nào khác).
  - Bất kỳ text thừa nào ngoài `[SILENT]` sẽ khiến cron runner chuyển tiếp tin nhắn rác hoặc spam tới chat của User.

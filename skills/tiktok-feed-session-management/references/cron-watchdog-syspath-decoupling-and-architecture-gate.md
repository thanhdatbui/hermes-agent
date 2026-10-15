# Cron Watchdog Syspath Decoupling & Architecture Gate Lessons

## Context & Root Cause (2026-10-15)
1. **ModuleNotFoundError khi Cronjob chạy script copy tại `%LOCALAPPDATA%`:**
   - Hermes cron khi cấu hình `script: "feed_session_watchdog.py"` sẽ sao chép hoặc trỏ script tại `%LOCALAPPDATA%\hermes\scripts\feed_session_watchdog.py`.
   - Khi chạy qua Python runner của Hermes, `sys.path[0]` là `%LOCALAPPDATA%\hermes\scripts`.
   - Nếu script repo (`D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`) được modular hóa thành package con (ví dụ `scripts/watchdog/`), script copy tại `%LOCALAPPDATA%` sẽ văng lỗi `ModuleNotFoundError: No module named 'watchdog'` hoặc `'scripts'`.
   - **Giải pháp dứt điểm:** Cấu hình cronjob dùng `prompt` gọi trực tiếp đường dẫn tuyệt đối trong repo với working directory tương ứng:
     `prompt: 'Chạy python "D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py" và xuất kết quả.'`
     `workdir: "D:\\Taadaa\\tiktok-luot nuoi acc\\scripts"`

2. **Architecture Gate Line Budget (<= 1450 lines):**
   - Repo `tiktok-luot nuoi acc` có test `tests/test_watchdog_architecture_gate.py::test_feed_session_watchdog_line_budget` giới hạn cứng `feed_session_watchdog.py` <= 1450 dòng.
   - Khi thêm helper functions, metrics counters, hoặc guards, bắt buộc phải kiểm tra `wc -l scripts/feed_session_watchdog.py` trước khi commit để không làm sập CI test suite.

3. **Dual-file Sync Parity:**
   - Cả 2 file `scripts/feed_session_watchdog.py` và `scripts/hermes_cron/feed_session_watchdog.py` có test kiểm tra parity `test_reconcile_helpers_in_sync_with_hermes_cron`.
   - Khối helper (`RECONCILE_METRICS: dict` đến trước `def reconcile_cluster_following(`) bắt buộc phải khớp nhau từng ký tự.

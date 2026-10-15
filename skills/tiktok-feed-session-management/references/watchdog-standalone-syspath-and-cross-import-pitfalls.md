# Watchdog Standalone sys.path Bootstrapping & Cross-Import Invariants

## Context & The 15/10/2026 Incident

Một session trước tự ý bóc tách `feed_session_watchdog.py` (monolith) thành package `scripts/watchdog/` (`lock.py`, `merger.py`, `alerts.py`, ...).
Hậu quả nghiêm trọng:
1. **Mất sys.path khi chạy Cron:** Hermes cron chạy script từ `%LOCALAPPDATA%\hermes\scripts\feed_session_watchdog.py`. Thư mục này không có package con `watchdog/`, dẫn đến:
   `ModuleNotFoundError: No module named 'watchdog'`
2. **Hiệu ứng sập chùm (Cross-Import Cascade):** `follow_session_watchdog.py` import `feed_session_watchdog` (`import feed_session_watchdog as fsw`). Khi feed watchdog lỗi dòng import, **cả report follow đang ổn định cũng bị kéo chết chùm**, làm gián đoạn toàn bộ kênh báo cáo Telegram của cả 2 mảng Nuôi và Follow.
3. **Chữa sai hướng (Spam L2 Commits):** Các session sau thấy cron lỗi thay vì kiểm tra `sys.path` thì lại đi sửa regex, sửa window time, sửa workdir, tạo ra hàng loạt commit rác và làm sai lệch baseline following.

---

## Invariants & Rules

1. **Standalone Entrypoint Sys.Path Bootstrapping:**
   Mọi script watchdog được deploy sang `%LOCALAPPDATA%` hoặc gọi từ bất kỳ thư mục nào BẮT BUỘC phải tự bootstrap đường dẫn repo vào đầu file:
   ```python
   import os, sys
   _candidate_dirs = [
       os.path.dirname(os.path.abspath(__file__)),
       r"D:\Taadaa\tiktok-luot nuoi acc\scripts",
       r"D:\Taadaa\tiktok-luot nuoi acc",
   ]
   for _d in _candidate_dirs:
       if os.path.isdir(_d) and _d not in sys.path:
           sys.path.insert(0, _d)
   ```

2. **Cấu hình Cronjob Gọi Canonical Script:**
   Không dùng cronjob dạng copy file vào `%LOCALAPPDATA%` đối với các module có dependencies nội bộ phức tạp. Cấu hình cronjob gọi trực tiếp canonical script trong repo:
   `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py"` với `workdir: D:\Taadaa\tiktok-luot nuoi acc\scripts`.

3. **Bảo vệ Cross-Import:**
   Script `follow_session_watchdog.py` khi import từ `feed_session_watchdog.py` chỉ nên import các pure helper function đã được kiểm tra isolation, không import toàn bộ module top-level nếu module đó có side-effects hoặc cấu trúc thư mục phụ thuộc.

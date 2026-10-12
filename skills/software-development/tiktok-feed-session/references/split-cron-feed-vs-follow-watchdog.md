# Quy chuẩn chia tách Cronjob: Lướt Feed vs Follow Chéo

## 1. Nguyên nhân sự cố lệch tin nhắn
- Việc gộp nhiều logic gửi tin vào 1 cronjob và dùng script tự mở raw urllib để dispatch sang các nhóm khác ngoài target gốc của cronjob (`deliver`) dẫn tới lỗi nuốt exception âm thầm khi gặp sự cố mạng hoặc timeout.
- Kết quả: Nhóm Nuôi Acc (Lướt Feed) nhận được báo cáo do Hermes Daemon điều phối, trong khi nhóm Follow bị mất tin hoàn toàn.

## 2. Giải pháp kiến trúc chuẩn (User chốt 2026-10-12)
- Tách bạch 100% nhiệm vụ theo Single Responsibility:
  - `tiktok-feed-session-watchdog` -> `feed_session_watchdog.py` -> `deliver: telegram:-5377611430` (Nuôi Acc).
  - `tiktok-follow-session-watchdog` -> `follow_session_watchdog.py` -> `deliver: telegram:-5127276494` (Follow).
- Mỗi watchdog:
  - In kết quả ra `stdout`.
  - Quản lý `STATE_FILE` và `ProcessLock` riêng biệt.
  - Hermes Cron Engine tự đảm nhiệm việc retry và push tin, tuyệt đối không gọi Telegram raw trong script.

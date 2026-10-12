# Dedicated Follow Cron Watchdog Architecture & Anti-Pattern

## 1. Bối cảnh & Vấn đề (Incident 2026-10-12)
- Khi hoàn tất một phiên nuôi acc (Ca 1 Phiên 1), hệ thống có 2 nhóm kết quả cần báo cáo:
  1. **Lướt Feed**: Cần gửi về nhóm `Tiktok Luot Nuoi Acc` (`-5377611430`).
  2. **Follow chéo**: Cần gửi về nhóm `Tiktok Follow` (`-5127276494`).
- **Anti-pattern cũ (Commit 125ec21):**
  - Giữ 1 cronjob duy nhất `tiktok-feed-session-watchdog`.
  - Script tự split string: Lướt Feed thì in ra `stdout` cho Hermes Cron gửi, còn Follow thì script tự mở socket raw HTTP `urllib.request.urlopen` bắn sang Telegram API.
  - Đoạn raw HTTP này bọc trong `try...except Exception` nuốt lỗi. Khi rớt mạng hoặc socket timeout, tin nhắn Follow bị mất vĩnh viễn, trong khi Lướt Feed vẫn gửi bình thường và script exit 0, state ghi nhận đã báo cáo xong.
  - Người dùng thấy "Lướt nuôi gửi được mà Follow mất tăm", tạo cảm giác vô lý và khó kiểm soát.

## 2. Nguyên tắc Kiến trúc Chuẩn (Single Responsibility Cronjobs)
Theo chỉ đạo thiết kế của User: **Mỗi loại báo cáo phải là một Cronjob độc lập trong Hermes**:

| Cronjob Name | Script | Deliver Target | State File |
| :--- | :--- | :--- | :--- |
| `tiktok-feed-session-watchdog` | `feed_session_watchdog.py` | `telegram:-5377611430` (Nuôi Acc) | `cron-state/feed_session_reported.json` |
| `tiktok-follow-session-watchdog` | `follow_session_watchdog.py` | `telegram:-5127276494` (Follow) | `cron-state/follow_session_reported.json` |

## 3. Quy chuẩn thực thi cho từng Watchdog
1. **Hermes Native Delivery:**
   - 100% báo cáo in ra `stdout`.
   - Giao việc gửi tin cho Hermes Gateway Scheduler chịu trách nhiệm (đảm bảo retry, queue, connection pool).
   - CẤM TUYỆT ĐỐI tự nhồi raw HTTP `urllib.request.urlopen` trong tiến trình con để bắn tin sang các nhóm khác.
2. **State & Lock Isolation:**
   - Mỗi watchdog có `STATE_FILE` riêng (`feed_session_reported.json`, `follow_session_reported.json`).
   - Mỗi watchdog có `ProcessLock` riêng (`<state_file>.proc_lock`), không tranh chấp lock với nhau.
3. **Silent Semantics:**
   - Khi phiên chưa xong hoặc không có dữ liệu cần báo cáo: script không in gì ra stdout (`output == ""`).
   - Hermes Cron thấy stdout rỗng sẽ tự động im lặng (silent run), không spam thông báo rác.

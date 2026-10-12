# Kiến Trúc Tách Biệt Cron Watchdog Báo Cáo Follow Chéo

## 1. Bối cảnh & Vấn đề kiến trúc (Anti-pattern gộp kênh)
- **Thiết kế lỗi cũ:** Script `feed_session_watchdog.py` tổng hợp cả Nuôi feed, Follow chéo và Upload video.
  - Phần Feed in ra `stdout` để Hermes Cron gửi về nhóm `Tiktok Luot Nuoi Acc` (-5377611430).
  - Phần Follow và Upload bị tách ra gửi ngầm bằng raw `urllib.request.urlopen` trong Python tới nhóm `Tiktok Follow` (-5127276494) và `Tiktok video` (-5435853713).
- **Hậu quả nghiêm trọng:**
  - Socket HTTP đơn lẻ của tiến trình Python thoáng qua (ephemeral process) dễ bị nghẽn mạng/timeout.
  - Bị nuốt lỗi âm thầm (`try...except logger.warning`) khiến script vẫn exit 0.
  - Hermes cron tưởng thành công nên persist `reported_sessions`, dẫn đến **mất hẳn báo cáo Follow trong khi báo cáo Feed vẫn gửi bình thường**.

## 2. Nguyên tắc bất di bất dịch: Single Responsibility Cronjobs
1. **Một Cronjob = Một Kênh Đích = Một Nhiệm vụ rõ ràng:**
   - CẤM TUYỆT ĐỐI tự mở socket raw `urllib` bắn chéo sang các kênh Telegram khác bên trong một script watchdog.
   - Mọi báo cáo định kỳ BẮT BUỘC phải đi qua **Hermes Cron Native Delivery** (`no_agent=True`, bắt `stdout` của script để Hermes Gateway chuyển tiếp).
2. **State & Process Lock độc lập:**
   - Mỗi mảng chức năng phải có `STATE_FILE` và `ProcessLock` riêng:
     - Feed: `feed_session_reported.json` & `.proc_lock`
     - Follow: `follow_session_reported.json` & `.proc_lock`
   - Nhờ tách biệt, việc một kênh bị nghẽn hay retry không làm ảnh hưởng đến tiến độ báo cáo của kênh kia.
3. **Phân rã script watchdog:**
   - `feed_session_watchdog.py`: Chỉ in báo cáo Nuôi feed ra `stdout` -> Hermes deliver `telegram:-5377611430`.
   - `follow_session_watchdog.py`: Chỉ in báo cáo Follow chéo ra `stdout` -> Hermes deliver `telegram:-5127276494`.
   - Khi không có dữ liệu mới hoặc chưa chốt ca: `stdout` rỗng (Hermes tự động silent run).

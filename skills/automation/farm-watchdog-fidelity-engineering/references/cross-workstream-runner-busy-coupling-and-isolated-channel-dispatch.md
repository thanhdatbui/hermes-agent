# Cross-Workstream Runner Busy Coupling & Isolated Channel Dispatch

## 1. Hiện Tượng (Failure Mode)
- Watchdog báo cáo nuôi acc / follow chéo bỗng nhiên "ngọng" toàn bộ (hoàn toàn không gửi tin nhắn Telegram nào ra nhóm), dù các phiên nuôi trong ngày đã chạy hoàn tất.
- File state `feed_session_reported.json` và `follow_session_reported.json` vẫn ghi nhận phiên đã báo cáo (`reported_sessions`), nhưng trên nhóm Telegram hoàn toàn không có tin nhắn.
- Hermes cron logs ghi nhận `Status: silent (empty output)`.

## 2. Nguyên Nhân Gốc Rễ (Root Causes)

### A. Coupling Tiến Trình Trong `is_feed_runner_active()` (False-Busy Deadlock)
- Hàm kiểm tra runner bận của watchdog nuôi feed lại chứa cả các pattern của luồng upload/avatar:
  ```python
  runner_patterns = (
      "multi_machine_feed_session",
      "multi-machine-feed-session",
      "run-feed-session.ps1",
      "run_follow",
      "run_tiktok.py",
      "hermes_cron_runner.py",
      "tiktok_runner.py",
      "run_post.py",        # <-- LỖI: Thuộc luồng upload video
      "tiktok_workflow",    # <-- LỖI: Thuộc luồng upload avatar/video
      "tiktok_upload",      # <-- LỖI: Thuộc luồng upload avatar/video
  )
  ```
- Khi các tác vụ nền như `post_evening_avatar_watchdog` hoặc batch upload kích hoạt trong khung giờ rảnh (09:30 - 11:30), watchdog nuôi feed & follow ngộ nhận là phiên nuôi vẫn đang chạy (`runner_busy = True`).
- Rào chắn `if is_today and runner_busy: return False` trong `can_report_session()` liên tục chặn không cho xuất báo cáo.

### B. Phantom Delivery Confirmation (Two-Phase Commit Rỗng)
- Khi watchdog chuẩn bị bản tin vào `pending_delivery`, ở tick tiếp theo nó kiểm tra `_get_hermes_delivery_error()` đọc `last_delivery_error` trong `jobs.json`.
- Nếu job chạy script ra stdout rỗng (do runner busy chặn xuất), Hermes ghi nhận `last_status: ok`, `last_delivery_error: null`.
- Watchdog thấy `delivery_err is None` liền tưởng nhầm tin nhắn trước đã được gửi thành công, vội vàng commit `reported.add(session_key)` và xóa `pending_delivery`. Phiên bị nuốt trọn vào trạng thái im lặng vĩnh viễn.

---

## 3. Quy Tắc & Chuẩn Hóa Bắt Buộc (Invariants)

1. **Phân Lập Tuyệt Đối Pattern Giữa Các Luồng (Decoupled Runner Patterns):**
   - Bộ lọc `is_feed_runner_active()` của watchdog nuôi feed CHỈ ĐƯỢC CHỨA các tiến trình lướt feed:
     `('multi_machine_feed_session', 'multi-machine-feed-session', 'run-feed-session.ps1', 'run_follow', 'run_tiktok.py', 'hermes_cron_runner.py', 'tiktok_runner.py')`.
   - TUYỆT ĐỐI CẤM đưa các tiến trình upload (`tiktok_upload`, `tiktok_workflow`, `run_post.py`), render hay 2FA vào bộ lọc busy của feed runner.

2. **Kỷ Luật "Script Nào Báo Cáo Về Đúng Nhóm Đó - Cấm Chung Đụng":**
   - **Nuôi acc / Lướt Feed:** Báo cáo về đúng nhóm **Tiktok Luot Nuoi Acc** (`-5377611430`).
   - **Follow chéo:** Báo cáo về đúng nhóm **Tiktok Follow** (`-5127276494`).
   - **Đăng Video / Avatar:** Báo cáo về đúng nhóm **Tiktok video** (`-5435853713`).
   - Tuyệt đối không gộp chung nội dung follow/video vào bản tin feed hoặc bắn chéo kênh gây nhiễu luồng giám sát.

3. **Cơ Chế Phục Hồi Khi Watchdog Bị Nuốt Phiên (Remediation):**
   - Khi phát hiện watchdog bị im lặng nhưng phiên đã hoàn tất:
     1. Kiểm tra và gỡ bỏ coupling pattern gây false-busy trong `scripts/watchdog/lock.py`.
     2. Dọn sạch `session_key` bị kẹt ảo trong cả 2 file:
        - `D:/Taadaa/runtime/kibe/cron-state/feed_session_reported.json`
        - `D:/Taadaa/runtime/kibe/cron-state/follow_session_reported.json`
     3. Watchdog sẽ tự động quét lại date live root và re-emit báo cáo về đúng từng nhóm ở tick cron kế tiếp.

# Watchdog False-Busy Deadlock & Two-Phase Commit Phantom Confirmation

## 1. Sự Cố: Watchdog Nuôi Acc / Follow Đột Nhiên "Ngọng" Cả Buổi Sáng

### Hiện Tượng:
- Các phiên nuôi feed hoặc follow (ví dụ Ca 1 Phiên 1 lúc 06:00, Phiên 2 lúc 08:00) đã hoàn thành thực tế trên cả hai cụm Kibe và Admin (thể hiện qua `summary.txt`, `log.jsonl`, và `session_action_stats` trong SQLite).
- Tuy nhiên, trên các nhóm Telegram (`-5127276494` và `-5377611430`) hoàn toàn không nhận được bất kỳ tin nhắn báo cáo nào.
- State file (`feed_session_reported.json` và `follow_session_reported.json`) lại ghi nhận session đã hoàn tất (`reported_sessions` chứa session key), khiến watchdog vĩnh viễn không bao giờ phát lại báo cáo.

---

## 2. Nguyên Nhân Gốc Rễ (Dual-Root Cause)

### A. False-Busy Deadlock (Nhận diện tiến trình bận chéo pipeline)
- Trong `feed_session_watchdog.py`, hàm `is_feed_runner_active()` gom chung các pattern regex kiểm tra tiến trình đang chạy:
  ```python
  runner_patterns = (
      "multi_machine_feed_session",
      "multi-machine-feed-session",
      "run-feed-session.ps1",
      "run_follow",
      "run_tiktok.py",
      "hermes_cron_runner.py",
      "tiktok_runner.py",
      "run_post.py",
      "tiktok_workflow",
      "tiktok_upload",
  )
  ```
- **Lỗ hổng:** `tiktok_workflow` và `tiktok_upload` thuộc về pipeline Upload Video / Upload Avatar (chạy qua `post_evening_avatar_watchdog.py` hoặc các cron upload chạy ngầm giữa các ca).
- Khi có tiến trình upload chạy trong khung giờ rảnh, `is_feed_runner_active()` trả về `True`.
- Tại hàm quyết định chốt sổ:
  ```python
  if is_today and runner_busy:
      return False
  ```
- Điều này biến watchdog thành trạng thái **Deadlock**: Session feed đã xong từ lâu nhưng watchdog luôn nghĩ là "runner đang bận" nên từ chối xuất báo cáo.

### B. Two-Phase Commit Phantom Confirmation (Xác nhận ảo từ jobs.json)
- Watchdog áp dụng cơ chế 2 pha:
  1. **Pha 1 (Emit):** Lưu tin nhắn vào `pending_delivery` và `print(msg)` ra stdout để Hermes cron nhận diện và bắn Telegram.
  2. **Pha 2 (Confirm):** Ở nhịp tick kế tiếp (5 phút sau), gọi `_get_hermes_delivery_error(mode)` đọc `last_delivery_error` trong `jobs.json`.
- **Lỗ hổng:** Hermes cron chỉ ghi nhận `last_delivery_error` khi Hermes thực sự cố gắng dispatch tin nhắn và bị Telegram API trả về lỗi. Nếu tiến trình con bị nuốt stdout (do forwarding shim với cờ `0x08000000` CREATE_NO_WINDOW trên Windows, buffer pipe bị nghẽn, hoặc process crash âm thầm), stdout trả về rỗng (`Status: silent (empty output)`).
- Khi stdout rỗng, Hermes cron coi như không có tin nhắn cần gửi $\to$ `last_delivery_error` vẫn là `None`!
- Ở Pha 2, watchdog thấy `delivery_err is None` liền lầm tưởng tin nhắn đã được gửi thành công $\to$ Commit session vào `reported_sessions` và xóa `pending_delivery`!
- **Hậu quả:** Báo cáo bị mất hoàn toàn trên Telegram nhưng trong DB/state vẫn ghi nhận đã gửi.

---

## 3. Quy Tắc & Giải Pháp Cơ Giới Hóa (Invariants)

1. **Phân rã phạm vi Busy Check (Scope Isolation):**
   - Bộ lọc kiểm tra tiến trình bận của Feed/Follow (`is_feed_runner_active()`) **CHỈ ĐƯỢC PHÉP** kiểm tra các tiến trình trực tiếp của Feed Session: `multi_machine_feed_session`, `run-feed-session.ps1`, `tiktok_runner.py`.
   - **CẤM TUYỆT ĐỐI** đưa các pattern của Upload Avatar, Video Post (`tiktok_upload`, `tiktok_workflow`, `run_post.py`) vào feed runner busy check.

2. **Chống Phantom Confirmation (Strict Telemetry Receipt):**
   - Không được phép coi `last_delivery_error is None` là bằng chứng giao tin thành công nếu không đối soát với `last_run_at` và độ dài output tối thiểu (> 200 bytes) của cron run.
   - Nếu output trong `cron/output/<job_id>/` là `silent (empty output)`, state machine BẮT BUỘC giữ nguyên `pending_delivery` để thử re-emit thay vì vội vàng commit vào `reported_sessions`.

3. **Bảo toàn Stdout trên Forwarding Shim Windows:**
   - Các forwarding shim chạy bằng `subprocess.run` trên Windows phải đảm bảo `stdout` và `stderr` được pipe hoặc inherit chuẩn xác; tránh để cờ `CREATE_NO_WINDOW` (0x08000000) ngắt kết nối handle đầu ra của tiến trình con.

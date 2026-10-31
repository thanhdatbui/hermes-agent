# Runner-Busy Filter Pollution & Two-Phase Delivery Phantom Confirmation

## 1. Hiện Tượng (Symptom)
- Watchdog định kỳ (Feed watchdog, Follow watchdog) đột ngột "ngọng", hoàn toàn im lặng (`Status: silent (empty output)`) cả buổi sáng dù các phiên nuôi máy thật đã chạy xong trọn vẹn.
- Database (`session_action_stats`) ghi nhận đủ số liệu của phiên, nhưng Telegram không hề nhận được bất kỳ tin nhắn nào.
- File state (`feed_session_reported.json`, `follow_session_reported.json`) đã tự động đánh dấu các session là `reported_sessions`, khiến các tick cron tiếp theo vĩnh viễn bỏ qua và không bao giờ gửi lại.

---

## 2. Nguyên Nhân Gốc Rễ (Root Cause)

### A. Ô nhiễm bộ lọc tiến trình bận (`is_feed_runner_active` Filter Pollution)
- Hàm kiểm tra `is_feed_runner_active()` quét danh sách tiến trình hệ thống qua `psutil` để tránh chốt non khi ca nuôi đang chạy dở.
- Tuy nhiên, bộ lọc `runner_patterns` vô tình chứa cả các tác vụ chạy nền không thuộc vòng đời nuôi feed:
  ```python
  runner_patterns = (
      "multi_machine_feed_session",
      "multi-machine-feed-session",
      "run-feed-session.ps1",
      "run_follow",
      "run_tiktok.py",
      "hermes_cron_runner.py",
      "tiktok_runner.py",
      "run_post.py",        # <-- LỖI: Thuộc upload video
      "tiktok_workflow",    # <-- LỖI: Thuộc render/upload
      "tiktok_upload",      # <-- LỖI: Thuộc upload avatar/video
  )
  ```
- Khi các watchdog cuốn chiếu (ví dụ `post-evening-avatar-watchdog` hoặc `run_tiktok_upload_batch.ps1`) chạy nền vào khung giờ nghỉ (09:00 - 12:00), `is_feed_runner_active()` liên tục trả về `True`.
- Điều kiện `can_report_session()` có rào chắn cứng:
  ```python
  if is_today and runner_busy:
      return False
  ```
  khiến watchdog nuôi feed và follow chéo bị nghẽn vĩnh viễn không thể chốt báo cáo.

### B. Lỗ hổng Two-Phase Commit "Xác nhận ảo" (Phantom Confirmation)
- Watchdog sử dụng cơ chế Two-Phase Delivery:
  - **Tick N**: Sinh bản tin, lưu vào `pending_delivery`, in ra `stdout` để Hermes cron bắt lấy và gửi Telegram.
  - **Tick N+1**: Gọi `_get_hermes_delivery_error()` kiểm tra trường `last_delivery_error` trong `jobs.json`. Nếu `delivery_err is None`, commit session vào `reported_sessions` và xóa `pending_delivery`.
- **Cái bẫy:** Với Hermes cronjob `no_agent=True`, stdout rỗng (`empty`) được coi là trạng thái hợp lệ (`Status: silent (empty output)`) và `last_delivery_error` vẫn là `None`!
- Nếu ở Tick N, tiến trình con bị nuốt stdout (do forwarding shim `creationflags=0x08000000` hoặc lỗi buffer), Hermes không gửi tin đi nhưng cũng không ghi nhận lỗi.
- Sang Tick N+1, watchdog thấy `delivery_err is None` liền lầm tưởng tin đã phát thành công $\to$ Commit vào `reported_sessions` $\to$ Mất dấu bản tin vĩnh viễn.

---

## 3. Quy Tắc Khắc Phục & Chuẩn Hóa Bắt Buộc (Invariants)

1. **Cô lập ranh giới runner patterns:**
   - `is_feed_runner_active()` CHỈ ĐƯỢC CHỨA các tiến trình lướt nuôi acc cốt lõi:
     ```python
     runner_patterns = (
         "multi_machine_feed_session",
         "multi-machine-feed-session",
         "run-feed-session.ps1",
         "run_follow",
         "run_tiktok.py",
         "hermes_cron_runner.py",
         "tiktok_runner.py",
     )
     ```
   - Tuyệt đối KHÔNG đưa các tiến trình upload video, avatar, render hay GPM vào bộ lọc bận của feed watchdog.

2. **Phân lập tuyệt đối các kênh báo cáo:**
   - **Nuôi Feed / Lướt Acc:** `feed_session_watchdog.py` $\to$ Nhóm **Tiktok Luot Nuoi Acc** (`-5377611430`).
   - **Follow chéo:** `follow_session_watchdog.py` $\to$ Nhóm **Tiktok Follow** (`-5127276494`).
   - **Đăng Video / Render:** `cron_post_upload_sync.py` $\to$ Nhóm **Tiktok video** (`-5435853713`).
   - Mỗi kênh phụ trách đúng nghiệp vụ của mình, không gộp số liệu hoặc để tác vụ kênh này gây nghẽn kênh kia.

3. **Phục hồi sự cố khi bị nghẽn báo cáo:**
   - Kiểm tra `is_feed_runner_active()` xem có tiến trình lạ nào đang chiếm cờ bận không.
   - Dọn sạch session bị xác nhận ảo trong `cron-state/feed_session_reported.json` và `follow_session_reported.json` (`reported_sessions.remove('<target_session>')` và đặt `pending_delivery = None`).
   - Để watchdog tự động quét lại và phát lại bản tin ở nhịp cron tiếp theo.

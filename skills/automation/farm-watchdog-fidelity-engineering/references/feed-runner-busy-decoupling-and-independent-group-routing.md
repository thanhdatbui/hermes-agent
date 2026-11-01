# Feed Runner Busy Decoupling & Independent Channel Routing

## 1. Sự Cố: False-Busy Deadlock do Gom Chung Process Pattern

### Hiện tượng:
- Watchdog nuôi acc (`feed_session_watchdog.py`) và watchdog follow chéo (`follow_session_watchdog.py`) bị "ngọng" hoàn toàn cả buổi sáng, không xuất bất kỳ báo cáo nào ra Telegram dù các ca nuôi `row-0-060026` và `row-0-080055` đã hoàn tất thành công.
- State file `feed_session_reported.json` và `follow_session_reported.json` bị commit ảo hoặc watchdog liên tục hoãn chốt sổ.

### Nguyên nhân gốc rễ:
- Hàm `is_feed_runner_active()` trong `scripts/watchdog/lock.py` quét danh sách tiến trình Windows (`psutil`) nhưng lại chứa các pattern của tác vụ upload nền:
  ```python
  # LỖI COUPLING:
  runner_patterns = (
      "multi_machine_feed_session",
      "run-feed-session.ps1",
      "tiktok_runner.py",
      "run_post.py",        # <-- Lỗi: Tiến trình đăng video
      "tiktok_workflow",    # <-- Lỗi: Engine render/upload video/avatar
      "tiktok_upload",      # <-- Lỗi: Script upload avatar/video nền
  )
  ```
- Khi các watchdog chạy nền lúc rảnh (ví dụ `post-evening-avatar-watchdog` chạy nạp avatar cho các nick mới/cựu binh lúc 09:30), tiến trình `run_tiktok_upload_avatar.ps1` và `tiktok_workflow` liên tục xuất hiện.
- Watchdog feed & follow ngộ nhận là **tiến trình nuôi acc vẫn đang chạy dở dâng** $\to$ `runner_busy = True` $\to$ kích hoạt rào chắn `if is_today and runner_busy: return False`, khiến watchdog bị kẹt cứng (deadlock) và không bao giờ chốt báo cáo.

### Chuẩn hóa & Quy tắc bắt buộc:
1. **Phân lập tuyệt đối bộ lọc runner busy (`is_feed_runner_active`):**
   - Chỉ giữ lại đúng các tiến trình thuộc vòng đời lướt nuôi acc:
     `('multi_machine_feed_session', 'multi-machine-feed-session', 'run-feed-session.ps1', 'run_follow', 'run_tiktok.py', 'hermes_cron_runner.py', 'tiktok_runner.py')`.
   - Tuyệt đối CẤM đưa các pattern upload avatar, render video, đăng bài (`tiktok_upload`, `tiktok_workflow`, `run_post.py`) vào bộ lọc này.
2. **Nguyên tắc "Script nào báo về nhóm nấy, không chung đụng":**
   - **Nuôi acc / Lướt feed (`feed_session_watchdog.py`):** Chỉ xuất số liệu lướt feed, tim, comment về nhóm **Tiktok Luot Nuoi Acc** (`-5377611430`). Lọc bỏ triệt để phần follow chéo và video.
   - **Follow chéo (`follow_session_watchdog.py`):** Chỉ xuất số liệu follow (Anchor M2, Bù M1, nick nhận, máy nhả) về nhóm **Tiktok Follow** (`-5127276494`).
   - **Đăng video / Render:** Chỉ xuất về nhóm **Tiktok video** (`-5435853713`).
3. **Phòng chống Phantom Confirmation ở Two-Phase Commit:**
   - Khi chạy qua forwarding shim, nếu child process bị nuốt stdout hoặc rơi vào `creationflags=0x08000000`, Hermes ghi nhận `Status: silent (empty output)` và `last_delivery_error: null`.
   - Watchdog không được coi `last_delivery_error is None` là bằng chứng gửi thành công nếu không có biên nhận thực tế, tránh commit nhầm session vào `reported_sessions`.

# Triage: Feed Session Watchdog Silent / Chậm báo cáo

## Nguyên nhân
Watchdog `feed_session_watchdog.py` có cơ chế `is_feed_runner_active()`:
- Watchdog chỉ tổng kết và gửi Telegram khi KHÔNG CÒN process runner feed nào đang chạy (`multi_machine_feed_session`, `multi-machine-feed-session`, `run-feed-session.ps1`).
- Nếu có một máy trong ca bị treo lệnh ADB (ví dụ: `exec-out screencap` hoặc `am force-stop` timed out, thiết bị treo I/O), subprocess của máy đó sẽ giữ tiến trình runner chính sống cho đến khi hết timeout toàn bộ retry.
- Trong suốt thời gian này, các tick cron 5 phút của watchdog đều ra `Status: silent (empty output)`.

## Quy trình chẩn đoán O(1)
1. **Kiểm tra tiến trình feed còn sống:**
   Dùng `psutil` để tìm PID của `multi-machine-feed-session` và quét các child process (`cmdline` chứa serial thiết bị nào, lệnh ADB nào đang chạy).
2. **Kiểm tra hiện trường log live của máy bị chậm:**
   - Xem thư mục: `D:\Taadaa\runtime\kibe\live\<YYYY-MM-DD>\row-<X>-<HHMMSS>\machines\<machine_id>\<timestamp>\`
   - Đọc cuối file `log.jsonl` để xem step và error (thường là `adb command timed out: screencap` hoặc `ATX_SESSION_UNAVAILABLE`).
3. **Kích hoạt / Verify báo cáo:**
   - Khi runner kết thúc hoàn toàn (hoặc sau khi xử lý tiến trình treo), chạy trực tiếp:
     `python C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`
   - Watchdog sẽ đọc kết quả toàn bộ máy từ thư mục live, in báo cáo ra stdout và đồng thời đẩy về kênh Telegram theo lịch.

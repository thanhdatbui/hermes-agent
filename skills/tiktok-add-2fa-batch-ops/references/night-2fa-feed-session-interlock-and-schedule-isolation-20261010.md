# Night TikTok 2FA Watchdog Interlock & Feed Session 2 Isolation (10/10/2026)

## 1. Sự Cố Xung Đột Đêm Khung 01:00 - 02:30 (Root Cause Anatomy)
- **Cấu trúc Ca 4 Nuôi Acc (Đêm):**
  * Phiên 1 (Feed only): `00:00` -> kết thúc lúc ~`01:00`.
  * Khoảng nghỉ giữa 2 phiên (Inter-session gap): `01:00` -> `01:30`.
  * Phiên 2 (Feed + Upload): `01:30` -> kết thúc lúc `02:35 - 02:45`.
- **Cơ chế lỗi của Watchdog cũ:**
  * Schedule đặt `*/10 1,2 * * *` với `in_window: 01:00 - 02:50`.
  * Hàm `is_feed_runner_active()` chỉ kiểm tra tiến trình `psutil` real-time (`multi_machine_feed_session` có đang chạy hay không).
  * Vào lúc `01:30:08`, Phiên 1 đã kết thúc, Phiên 2 chưa kịp spawn (`is_feed_runner_active() == False`).
  * Watchdog 2FA ngộ nhận farm rảnh, kích hoạt `run_batch_live_2fa.py` và chiếm Device Locks trên hàng loạt máy.
  * Lúc `01:32:23`, Phiên 2 bắt đầu chạy thì thấy máy bị lock nên buộc phải skip toàn bộ 30+ máy (`skipped-device-locked`).

## 2. Giải Pháp Phòng Vệ 2 Tầng (Two-Tier Interlock Protection)

### Tầng 1: Khóa Liên Động Trạng Thái (State Interlock Gate `is_ca4_finished`)
- Tuyệt đối không chỉ dựa vào `is_feed_runner_active()` (vì giữa 2 phiên có khe rỗng 30 phút).
- Bắt buộc kiểm tra trực tiếp sổ cái báo cáo `feed_session_reported.json` (`TAADAA_REPORTED_FILE`):
```python
REPORTED_FILE = Path(os.getenv("TAADAA_REPORTED_FILE", "D:/Taadaa/runtime/kibe/cron-state/feed_session_reported.json"))

def is_ca4_finished(today_str: str) -> bool:
    """Kiểm tra Ca 4 Phiên 2 đã hoàn tất và đã được Watchdog báo cáo hay chưa."""
    if not REPORTED_FILE.is_file():
        return False
    try:
        data = json.loads(REPORTED_FILE.read_text(encoding="utf-8"))
        sessions = set(data.get("reported_sessions", []))
        return f"{today_str}_ca4_phien2" in sessions or f"{today_str}_ca4" in sessions
    except Exception as exc:
        logger.warning("Lỗi kiểm tra trạng thái Ca 4: %s", exc)
        return False
```
- Khi `not is_ca4_finished(today_str)`, watchdog thoát an toàn ngay lập tức (`return 0`), triệt tiêu 100% khả năng chạy chen giữa Phiên 1 và Phiên 2.

### Tầng 2: Dời Cửa Sổ Giờ Schedule Sang Sau Ca 4 (Post-Ca-4 Window)
- Chuyển `in_window` sang khung giờ: `02:45 - 04:50` (hoặc `03:00 - 04:50`):
  ```python
  in_window = (now.hour == 2 and now.minute >= 45) or (3 <= now.hour <= 4)
  ```
- Cập nhật Cron Schedule từ `*/10 1,2 * * *` thành `*/10 2,3,4 * * *` (hoặc `*/10 3,4 * * *`).
- Đảm bảo thứ tự chuỗi ban đêm:
  1. `00:00 - 01:00`: Ca 4 Phiên 1 (Feed only).
  2. `01:30 - 02:40`: Ca 4 Phiên 2 (Feed + Upload).
  3. `02:45 - 03:30`: Batch Add 2FA TikTok chạy an toàn (toàn bộ máy đã giải phóng lock).
  4. `03:30 - 04:00`: Dọn cache TikTok cuối ngày (`end-of-day-clear-tiktok-cache`).
  5. `04:00 - 06:00`: Farm nghỉ ngơi, làm mát thiết bị trước khi bắt đầu Ca 1 (06:00).

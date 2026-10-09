# Xung Đột Chí Mạng Giữa Cron Dọn Cache Và Ca Nuôi Feed Ban Đêm (Ca 4)

## 1. Hiện tượng thực tế (Incident 18/09/2026 - Ca 4 Đêm)
Người vận hành phát hiện: "Lướt feed fail gần một nửa" (chỉ 25/52 máy thành công, 27 máy bị lỗi hoặc dừng).

Bóc tách hiện trường O(1):
- Tổng farm: 80 máy.
- 28 máy không có tài khoản cấu hình ở Row 8 (`account row 8 is empty (no username), skipping`).
- 52 máy có tài khoản:
  - 25 máy `success` (48%).
  - 9 máy `skipped-device-locked` (M16, M23, M27, M29, M34, M38, M59, M71, M80).
  - 9 máy `manual-needed` (M19, M33, M47, M50, M56, M70, M72, M78, M79).
  - 7 máy `fail` (M09, M39, M49, M51, M60, M68, M74).
  - 2 máy `failed` (M43, M77).

## 2. Nguyên nhân gốc rễ (Root Cause)
### a) Lỗi cú pháp Cron Expression (`*/10 1,2,3,4 * * *`)
- Job cron `79021fa79d8b` (`end-of-day-clear-tiktok-cache`) ghi mục tiêu: *"Dọn dẹp bộ nhớ đệm TikTok (40 workers song song) cuối ngày (04:00 sáng)"*.
- Tuy nhiên cron expression bị cấu hình thành `*/10 1,2,3,4 * * *` (chạy mỗi 10 phút một lần liên tục từ 01:00 đến 04:59 sáng).
- Trong khung giờ Ca 4 (01:50 - 02:53), cron này kích hoạt liên tục (01:50, 02:00, 02:10, 02:20, 02:30, 02:40, 02:50).

### b) Lệnh Teardown Hủy Diệt Trong `cron_clear_tiktok_cache.py`
- Khối `finally` của `clear_device_cache` gửi lệnh ADB trực tiếp:
  ```bash
  am force-stop com.ss.android.ugc.trill; input keyevent KEYCODE_HOME;
  ```
- Khi 40 worker dọn cache chạy song song, nó cưỡng bức `force-stop` TikTok và bấm `KEYCODE_HOME` trên các máy đang lướt feed.
- Dẫn đến chuỗi lỗi đồng loạt:
  - `TikTok focus lost to launcher`
  - `focused package unavailable`
  - `screen capture invalid; feed not confirmed`
  - `feed swipe command failed`
  - `ATX_SESSION_UNAVAILABLE`

## 3. Quy tắc an toàn bắt buộc (Invariants)

1. **Kỷ luật cú pháp Cron Expression cho tác vụ cuối ngày:**
   - Tác vụ chỉ chạy 1 lần vào mốc giờ cố định BẮT BUỘC dùng cú pháp phút cụ thể:
     - Đúng: `0 4 * * *` (chạy đúng 04:00 sáng).
     - Sai: `*/10 1,2,3,4 * * *` (bắn phá 24 lần suốt đêm).

2. **Preflight Guard cho toàn bộ Maintenance Cron trên Farm:**
   - Bất kỳ script dọn dẹp, bảo trì, cache clear, Wi-Fi auto-healer, reboot nào chạm vào thiết bị BẮT BUỘC phải kiểm tra trước khi thực thi:
     ```python
     if is_feed_runner_active():
         logger.info("Feed runner is active, skipping maintenance action to prevent interference.")
         return
     ```
   - Nếu máy đang có device lock hoặc đang chạy feed session, tuyệt đối cấm gửi `am force-stop` hay `input keyevent KEYCODE_HOME`.

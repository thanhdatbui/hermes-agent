# Cảnh giác Báo động giả (False Alert) do Runner Trùng lặp & Watchdog kẹt Lock

## 1. Triệu chứng
- Watchdog gửi báo cáo tổng kết phiên với kết quả **đồng loạt fail toàn bộ farm** (ví dụ: Fail 78/80 máy), trong khi:
  - 0 lượt xem video.
  - 0 tim, 0 follow.
  - Thời gian chạy kết thúc bất thường chỉ sau vài giây hoặc vài phút.

## 2. Bản chất hiện tượng
1. **Trigger trùng lặp (Duplicate Runner):**
   - Runner chính `row-X-HHMMSS` (PID A) được spawn và acquire device lock toàn bộ máy để nuôi acc.
   - Một tiến trình runner thứ 2 vô tình bị trigger lặp ngay sau đó (sau 1-2 phút).
   - Tiến trình thứ 2 gặp lock do PID A đang giữ -> toàn bộ máy bị `skipped-device-locked` -> tiến trình 2 thoát ngay và sinh file `summary.txt` với event `skipped-device-locked`.
2. **Lỗi parse của Watchdog:**
   - Watchdog quét thấy artifact của tiến trình thứ 2 đã kết thúc, nhặt nhầm và parse root `summary.txt`.
   - Nếu parser gán nhầm `skipped-device-locked` thành `fail: batch-config-error`, watchdog sẽ ngộ nhận phiên đã hoàn tất thật và phát False Alert.

## 3. Quy trình O(1) xác minh hiện trường
1. **Kiểm tra process thật đang active:**
   ```bash
   tasklist | grep python
   # Hoặc kiểm tra psutil Process cmdline có chứa multi-machine-feed-session
   ```
2. **Kiểm tra các run folder trong ngày:**
   ```bash
   ls -lt "D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>" | head -n 10
   ```
   Nếu thấy 2 folder gần sát giờ nhau (ví dụ: `row-6-200025` và `row-6-200406`), kiểm tra `log.jsonl` của folder đang chạy dở:
   ```bash
   tail -n 20 "D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/<run_chinh>/log.jsonl"
   ```
   Nếu thấy các máy vẫn đang `success` (16-22 swipes), đây 100% là False Alert.

## 4. Xử lý máy trống slot (None ID)
- Khi phát hiện máy trống slot ở Row đang chạy (như M19, M74 ở Row 6):
  - Chạy O(1) detector: `python D:/Taadaa/Tiktok_Reg/_detect_clean.py` để kiểm tra danh sách target mail sạch.
  - Lưu ý: Cron tự động `post_noon_chain_watchdog` đã bỏ phase Reg TikTok tự động. Khâu reg bù cần chạy on-demand qua `_run_all_targets.py` khi farm rảnh giữa các ca.

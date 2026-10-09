# Xử lý Lỗi Watchdog Báo Cáo Ảo Khi Runner Trùng Lặp Bị Khóa Thiết Bị (Device Lock)

## 1. Triệu chứng & Bằng chứng thực tế (Case 80)
- Watchdog `feed_session_watchdog.py` gửi cảnh báo đỏ lên nhóm Farm Alert:
  ```
  📊 [TIKTOK NUÔI ACC] Ca 3 - Phiên 2/2 (Tối) hoàn tất (Row 6)
  • Lướt Feed:
    + Success (0): Không có
    + Fail (78): M1, M2, M3, M4, ...
  ```
- Tuy nhiên kiểm tra thực tế:
  - Phiên nuôi acc chính (`row-6-200406`) vẫn đang chạy bình thường và đạt tỉ lệ thành công cao (>93%, 72/77 máy pass).
  - Xuất hiện một thư mục chạy rác (`row-6-200025`) kết thúc sau 9s với `skipped-device-locked: 78`.

## 2. Nguyên nhân cốt lõi (Anti-Pattern)
1. **Runner kép (Concurrent Duplicate Trigger):**
   - Khi tiến trình runner thứ hai vô tình bị trigger lặp lại, toàn bộ các máy đã bị tiến trình chính chiếm giữ lock hợp lệ (`C:\Users\Kibe\.codex\device-locks\machine_N.lock.json`).
   - Runner thứ hai kết thúc ngay lập tức và ghi nhận 78 máy bị `skipped-device-locked`.
2. **Lỗi Parse Fallback trong Watchdog:**
   - Trong `feed_session_watchdog.py`, hàm `parse_run_all` khi duyệt thư mục root của runner thứ hai tìm thấy `summary.txt` (không nằm trong folder máy con) đã fallback dùng regex quét chuỗi `machine_(\d+)`.
   - Script mặc định gán: `{"status": "fail", "reason": "batch-config-error"}` cho tất cả các máy xuất hiện trong file summary.
   - Khi đó, bộ lọc `is_device_locked_skip` bị vô hiệu hóa hoàn toàn, khiến watchdog tưởng rằng 78 máy đã chạy thật và bị fail cấu hình, kích hoạt gửi Farm Alert ảo và chốt session sớm đè lên phiên chính.

## 3. Giải pháp chuẩn hóa (Case Fix)
1. **Ưu tiên đọc `log.jsonl` tại run root:**
   - Đọc trực tiếp trường `account`, `result` và `error` trong từng dòng json của `log.jsonl`.
   - Nếu kết quả ghi nhận `skipped-device-locked`, lưu nguyên trạng thái `status: skipped-device-locked` và lý do lock.
2. **Bảo toàn trạng thái Device Lock ở fallback `summary.txt`:**
   - Nếu fallback sang `summary.txt`, kiểm tra chuỗi `skipped-device-locked in c`.
   - Nếu toàn bộ bị lock, gán `default_st = "skipped-device-locked"` và `default_reason = "device-lock-active"`.
3. **Chặn chốt báo cáo khi còn lock:**
   - Bộ lọc `can_report_session` kiểm tra cờ `has_unattempted_locked`. Nếu các máy dự kiến vẫn đang bị lock (chưa có kết quả chạy thật), watchdog tuyệt đối KHÔNG được chốt báo cáo cho đến khi phiên chính nhả lock và hoàn tất.

# Phân tích Cơ chế Tọa độ Dynamic & Khắc phục ADB Swipe Timeout

## 1. Cơ chế Click & Tọa độ trong Automation (TikTok Feed Session)
- **Tọa độ không cố định:** Hệ thống dùng cơ chế dynamic coordinate calculation qua ATX-agent XML (port 7912).
- **Quy trình:**
  1. Đọc cây phân cấp UI XML qua ATX session.
  2. Dùng XPath/Selector tìm node mục tiêu (`text`, `content-desc`, `resource-id`).
  3. Lấy `bounds="[left,top][right,bottom]"` thực tế trên màn hình.
  4. Tính tâm động: `center_x = (left + right) // 2`, `center_y = (top + bottom) // 2`.
  5. Gửi lệnh `input tap <center_x> <center_y>`.
- **Swipe feed:** Tọa độ vuốt xuất phát từ `BASE_SWIPE_START` -> `BASE_SWIPE_END` có cộng rung lắc ngẫu nhiên `jitter_px` ($\pm 15-30$px) để tránh pattern cứng.

## 2. Khắc phục lỗi `adb command timed out` khi `input swipe`
- **Nguyên nhân:** Khi TikTok giải mã video nặng, CPU Samsung S7 bị nghẽn làm lệnh ADB shell `input swipe` với `duration_ms` dài (>1000ms) bị kẹt, vượt quá timeout 15s của Python `_run_bounded`.
- **Giải pháp chuẩn:**
  - Tăng `timeouts.adb_seconds` từ 15s lên 25s–30s trong `config.yaml`.
  - Giảm dải `min_swipe_duration_ms` / `max_swipe_duration_ms` về 450ms–700ms để lệnh shell kết thúc nhanh.
  - Bọc retry 1 lần khi gặp Timeout ở tầng `_perform_feed_swipe`.

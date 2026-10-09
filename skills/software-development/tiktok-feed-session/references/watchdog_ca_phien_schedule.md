# Watchdog Báo Cáo Nuôi TikTok: Cấu Trúc 4 Ca x 2 Phiên

Cập nhật: 2026-09-11

## 1. Cấu hình SESSION_WINDOWS (8 Windows)
Script: `AppData/Local/hermes/scripts/feed_session_watchdog.py`

- **Ca 1 (Sáng)**:
  - Phiên 1/2: 06:00 - 08:00
  - Phiên 2/2: 08:00 - 12:00 (Đăng video)
- **Ca 2 (Trưa / Chiều)**:
  - Phiên 1/2: 12:00 - 14:00
  - Phiên 2/2: 14:00 - 18:00 (Đăng video)
- **Ca 3 (Tối)**:
  - Phiên 1/2: 18:00 - 20:00
  - Phiên 2/2: 20:00 - 24:00 (Đăng video)
- **Ca 4 (Đêm)**:
  - Phiên 1/2: 00:00 - 01:30
  - Phiên 2/2: 01:30 - 06:00 (Đăng video)

## 2. Quy ước Khóa Session (`session_key`)
- State lưu trong `cron-state/feed_session_reported.json`.
- Key định dạng: `{target_date}_ca{ca}_phien{phien}` (ví dụ: `2026-09-11_ca1_phien1`, `2026-09-11_ca1_phien2`).
- Phải kèm trường `phien` để tránh báo cáo phiên 1 đè lên phiên 2 hoặc bỏ sót phiên 2 của cùng một ca.

## 3. Pitfall Boundary Giờ Cuối Ngày
- Khung giờ Ca 3 Phiên 2 có `end: "24:00"` (hoặc `"00:00"`). Nếu so sánh chuỗi thông thường `win["start"] <= r_hm < win["end"]`, chuỗi `"20:00"` đến `"23:59"` sẽ không thỏa mãn `< "00:00"`.
- Cách xử lý:
  ```python
  if win["end"] == "24:00" or win["end"] == "00:00":
      in_window = (r_hm >= win["start"])
  else:
      in_window = (win["start"] <= r_hm < win["end"])
  ```

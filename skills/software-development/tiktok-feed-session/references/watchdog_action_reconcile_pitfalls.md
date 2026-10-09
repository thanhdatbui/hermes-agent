# Watchdog Action Reconcile & Dashboard Pitfalls

## 1. Phân biệt Follow Chéo Nội bộ vs Follow Tự nhiên (Feed Session)
- Trong phiên nuôi lướt (`feed_session_watchdog.py`):
  - `m_to_cross[str(m)] = cnt`: Số lượt follow chéo nội bộ farm (`follow_data.get("followed", [])`).
  - `m_to_natural[str(m)] = natural_cnt`: Số lượt follow tự nhiên ngoài luồng theo từ khóa / video đề xuất.
  - `m_to_reported[str(m)] = cnt + natural_cnt`: Tổng lượt follow mà script báo cáo để đối soát delta web.
- **CẠM BẪY NGHIỆM TRỌNG:**
  - Bảng `daily_account_actions` trong `tiktok_tracker.db` có cột `internal_follows`.
  - CẤM lấy `r_cnt = m_to_reported` ghi vào `internal_follows`! Làm vậy sẽ biến toàn bộ follow tự nhiên (ví dụ follow các shop, nick meme capybara bên ngoài) thành follow nội bộ farm.
  - Chỉ được lấy `c_cnt = m_to_cross` (sau khi check `failed_reset_machines`) để ghi vào `internal_follows`.

## 2. Dashboard Mapping & Hiển thị
- `tiktok_dashboard.py` đọc `daily_account_actions.internal_follows` cho từng user và hiển thị badge `🔗 Nội bộ: +X`.
- Nếu phát hiện nick có badge `🔗 Nội bộ: +X` nhưng trong app TikTok thật sự danh sách Following không có bất kỳ nick nội bộ farm nào:
  1. Kiểm tra `session_action_stats` của phiên xem `internal_fl` có bằng 0 không.
  2. Kiểm tra `daily_account_actions` xem bản ghi được ghi lúc mấy giờ, có bị bug ghi gộp follow tự nhiên không.
  3. Dọn dẹp bản ghi sai trong `daily_account_actions` bằng SQLite query trực tiếp.

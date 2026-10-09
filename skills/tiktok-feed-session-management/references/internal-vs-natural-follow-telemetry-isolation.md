# Pitfall: Lệch Thống Kê Follow Nội Bộ vs Follow Tự Nhiên (Watchdog & Dashboard)

## Hiện Tượng (Symptom)
- Trên Web Dashboard (`tiktok_dashboard.py`), tài khoản hiển thị badge `🔗 Nội bộ: +N` (ví dụ `🔗 Nội bộ: +2`), nhưng khi kiểm tra trực tiếp danh sách `Đã follow` (Following) trên App TikTok của máy đó thì toàn bộ N tài khoản đều là nick bên ngoài (kênh trend, shop, đề xuất), không có bất kỳ nick nội bộ nào thuộc farm.

## Nguyên Nhân Gốc Rễ (Root Cause)
1. **Watchdog gom nhầm biến reported (`feed_session_watchdog.py`):**
   - Biến `m_to_reported[str(m)] = 0 if failed else cnt + natural_cnt` (trong đó `cnt` là follow chéo nội bộ, `natural_cnt` là follow tự nhiên lúc lướt feed).
   - Khi lưu thống kê cấp ngày vào bảng `daily_account_actions`, script lấy `r_cnt = m_to_reported.get(m_num, 0)` ghi thẳng vào cột `internal_follows`:
     ```python
     cur_w.execute("""
         INSERT INTO daily_account_actions (target_date, username, may, internal_follows, updated_at)
         VALUES (?, ?, ?, ?, ?)
         ON CONFLICT(target_date, username) DO UPDATE SET
             internal_follows = daily_account_actions.internal_follows + excluded.internal_follows,
             updated_at = excluded.updated_at
     """, (act_date, u_name.lower(), int(m_num) if str(m_num).isdigit() else None, r_cnt, now_ts))
     ```
   - Hậu quả: Toàn bộ số lượt follow tự nhiên (`natural_cnt`) bị gán nhầm thành `internal_follows`.

2. **Dashboard đọc và hiển thị nhầm (`tiktok_dashboard.py`):**
   - Dashboard truy vấn:
     `SELECT username, internal_follows FROM daily_account_actions WHERE target_date = ?`
   - Sau đó render:
     `🔗 Nội bộ: +${item.internal_followed}`
   - Dẫn đến việc các lượt follow kênh tự nhiên ngoài feed bị dán nhãn thành "Nội bộ: +N".

## Quy Tắc Đối Soát & Khắc Phục (Action Item)
- **Tách bạch 2 trường dữ liệu:** Bảng `daily_account_actions` cần lưu riêng rẽ cả `internal_follows` (lấy từ `cross_cnt`) và `natural_follows` (lấy từ `natural_cnt`), tương tự như cấu trúc của bảng `session_action_stats`.
- Khi đối soát follow giữa App và Dashboard:
  - Bắt buộc kiểm tra danh sách following trên TikTok thật so với bảng `farm_account_info` trong `D:/Taadaa/data/tiktok_tracker.db` để phân biệt nick nội bộ và nick tự nhiên.
  - Kiểm tra bảng `session_action_stats` để xem phiên chạy thực tế có phát sinh `internal_follows` hay không trước khi kết luận nick đã follow nội bộ.

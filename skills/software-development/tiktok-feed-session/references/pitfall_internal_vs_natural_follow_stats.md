# Pitfall: Lệch Thống Kê Follow Nội Bộ vs Follow Tự Nhiên (Watchdog & Dashboard)

## Hiện Tượng (Symptom)
- Trên Web Dashboard (`tiktok_dashboard.py`), tài khoản hiển thị badge `🔗 Nội bộ: +N` trong khi thực tế trên app TikTok tài khoản chỉ follow các kênh bên ngoài (kênh trend, shop, đề xuất), không có bất kỳ nick nội bộ nào thuộc farm.

## Nguyên Nhân Gốc Rễ (Root Cause)
1. **Watchdog gom nhầm biến reported (`feed_session_watchdog.py`):**
   - Biến `m_to_reported[str(m)] = 0 if failed else cnt + natural_cnt` (trong đó `cnt` là follow chéo nội bộ, `natural_cnt` là follow tự nhiên lúc lướt feed).
   - Khi lưu vào bảng `daily_account_actions`, script lấy `r_cnt = m_to_reported.get(m_num, 0)` ghi thẳng vào cột `internal_follows`:
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

2. **Dashboard hiển thị nhầm (`tiktok_dashboard.py`):**
   - Dashboard đọc trực tiếp `daily_account_actions.internal_follows` và render `🔗 Nội bộ: +N`.

## Quy Tắc Đối Soát & Khắc Phục (Action Item)
- **Tách bạch 2 trường dữ liệu:** Bảng `daily_account_actions` cần có cả 2 cột `internal_follows` (lấy từ `cross_cnt`) và `natural_follows` (lấy từ `natural_cnt`), tương tự như bảng `session_action_stats`.
- Khi đối soát follow giữa App và Dashboard:
  - Bắt buộc kiểm tra danh sách following trên TikTok thật so với bảng `farm_account_info` trong `D:/Taadaa/data/tiktok_tracker.db` để phân biệt nick nội bộ và nick tự nhiên.
  - Kiểm tra bảng `session_action_stats` để xem phiên chạy thực tế có phát sinh `internal_follows` hay không trước khi kết luận nick đã follow nội bộ.

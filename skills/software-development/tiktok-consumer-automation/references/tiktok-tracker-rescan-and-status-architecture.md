# TikTok Farm Account Tracker & Rescan Architecture

## 1. Overview & Components
Hệ thống theo dõi tài khoản TikTok toàn farm (`D:/Taadaa/tools/tiktok_account_tracker.py`) quản lý ~1.000 tài khoản farm trên cả 2 cụm (Kibe: máy 1..80, Admin: máy 201..280).

- **Database chính**: `D:/Taadaa/data/tiktok_tracker.db`
  - Bảng `snapshots`: Lưu lịch sử snapshot (follower, heart, video, status, avatar_thumb, has_avatar, timestamp).
  - Bảng `farm_account_info`: Lưu thông tin mapping máy, tik, host_id.
- **Web Dashboard**: `D:/Taadaa/tools/tiktok_dashboard.py` (cổng 1905).
- **Cronjob**: `daily-tiktok-farm-tracker` (07:00 hàng ngày qua `cron_tiktok_daily_tracker.py`).

---

## 2. Phân biệt Trạng thái & Cơ chế Tránh Báo Ảo
Khi crawler quét endpoint công khai `https://www.tiktok.com/@username` qua proxy pool:
- `LIVE`: TikTok trả về `statusCode: 0` và có object `userInfo`. Tài khoản đang hoạt động bình thường.
- `PENDING`: Tài khoản mới nạp vào database, chưa từng qua lượt quét thực tế nào (thường do import batch khởi tạo). **Không phải nick die**.
- `ERROR` / `RATE_LIMITED`: Timeout kết nối proxy, lỗi mạng hoặc gặp TikTok SlardarWAF. Cần thử lại với proxy khác, **không phải nick die**.
- `NOT_FOUND`: TikTok trả về `statusCode: 10221` hoặc HTTP 404 (tài khoản không tồn tại / đã bị xóa hoặc đổi username).

---

## 3. Cơ chế Quét Bổ Sung (Supplementary Rescan & Auto-Retry)

### A. Auto-Retry Trong Phiên Quét Chính (Pass 2)
Trong luồng daily scan thông thường:
- Sau khi hoàn thành pass 1, nếu có các nick bị `ERROR`, `RATE_LIMITED`, hoặc `NOT_FOUND` (số lượng ≤ 50% tổng số quét):
  - Tự động lọc danh sách lỗi và kích hoạt ngay **Pass 2** với proxy pool xoay vòng mới.
  - Kết quả `LIVE` ở Pass 2 sẽ ghi đè lên kết quả lỗi trước khi lưu vào DB SQLite và xuất báo cáo.
  - Cờ CLI điều khiển: `--auto-retry` (mặc định bật) / `--no-auto-retry`.

### B. Quét Bổ Sung Độc Lập (`--rescan-non-live`)
Khi cần bù số liệu cho các nick chưa `LIVE` mà không tốn tài nguyên quét lại toàn bộ 1.000 nick:
```bash
python D:/Taadaa/tools/tiktok_account_tracker.py --rescan-non-live --workers 10
```
- Truy vấn DB SQLite lọc các nick có snapshot mới nhất có `status != 'LIVE'`:
  ```sql
  WITH Ranked AS (
      SELECT username, status, ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC, id DESC) as rn
      FROM snapshots
  )
  SELECT username FROM Ranked WHERE rn = 1 AND status != 'LIVE'
  ```
- Tự động bù thông tin số máy (`may`) và `video_posted` từ bảng `farm_account_info` nếu nick chỉ tồn tại trong DB mà không có trong Excel hiện hành.
- Giúp Dashboard cập nhật ngay số liệu LIVE chuẩn xác 100% trong vòng vài chục giây.

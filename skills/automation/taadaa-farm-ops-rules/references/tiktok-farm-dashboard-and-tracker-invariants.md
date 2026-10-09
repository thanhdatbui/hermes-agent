# TikTok Farm Dashboard & Tracker Invariants

## 1. Midnight & Partial Scan Boundary (Chống co cụm số lượng nick sau 0h đêm)
- **Triệu chứng**: Vừa qua 0h đêm, watchdog nuôi acc (`feed_session_watchdog`) chạy đối soát nhanh cho một số máy (ví dụ 54 máy). Dashboard đột ngột tụt từ 1.042 nick xuống còn 54 nick, làm user hoang mang tưởng mất nick.
- **Nguyên nhân cốt lõi**: Câu query SQL lọc cứng `WHERE substr(timestamp, 1, 10) = max_date`. Khi bước qua ngày mới, `max_date` biến thành ngày hôm nay, khiến 988 nick của ngày hôm trước bị tạm ẩn sạch.
- **Quy tắc bất biến**:
  * Dashboard BẮT BUỘC hiển thị đầy đủ toàn bộ nick active của farm 24/24.
  * Truy vấn `LatestCurr` phải dùng cửa sổ trượt 2 ngày: `rn = 1 AND timestamp >= date(max_dt, '-2 days')`.
  * Truy vấn `RankedPrev` (để tính delta) phải lấy snapshot của ngày trước đó: `substr(s.timestamp, 1, 10) < substr(c.timestamp, 1, 10)`.
  * Nick nào vừa quét sau nửa đêm thì cập nhật số mới; nick nào chưa đến giờ quét sáng (07:00) thì giữ nguyên snapshot hôm trước, tuyệt đối không được ẩn đi.

## 2. Transient Scraper Glitch Guard (Chống tụt ảo / Phantom Drop do proxy timeout)
- **Triệu chứng**: Thẻ KPI Follower tự dưng báo đỏ `-17`, thẻ Following báo đỏ `-85`, dù thực tế toàn farm đang tăng trưởng.
- **Nguyên nhân cốt lõi**: Khi script cào (`fetch_profile`) bị nghẽn mạng/proxy timeout trên 1 nick (ví dụ `@m.ngc4624`), script trả về `status = ERROR` và gán mặc định `followerCount = 0`, `followingCount = 0`. Khi lưu snapshot, nick đó bị ghi nhận tụt từ 54 -> 0 và 109 -> 0, xóa sạch thành quả tăng trưởng của 30 nick khác trong farm.
- **Quy tắc bất biến**:
  * Các câu truy vấn `snapshots` trên Dashboard BẮT BUỘC phải có điều kiện `WHERE status != 'ERROR'`.
  * Khi 1 nick gặp sự cố proxy tạm thời, Dashboard phải tự động bỏ qua snapshot lỗi đó và giữ lại snapshot `LIVE` hợp lệ gần nhất.
  * Khi phân tích biến động âm cho user: Kiểm tra ngay các nick có `status != 'LIVE'` hoặc `delta` âm bất thường để phân biệt tụt thật vs lỗi cào mạng.

## 3. String Formatting trên Delta âm (Chống lỗi `+-85`)
- Tuyệt đối không nối chuỗi thủ công kiểu `+${delta}` hoặc `'+' + str(delta)`.
- Khi `delta < 0`:
  * Nhãn: `📉 Tổng giảm:` (màu đỏ `#ef4444`).
  * Giá trị: hiển thị trực tiếp số âm (`-85`), không gắn thêm dấu `+`.
- Khi `delta >= 0`:
  * Nhãn: `📈 Tổng tăng:` (màu xanh `#22c55e`).
  * Giá trị: gắn thêm dấu `+` (`+24`).

## 4. Biểu Đồ Tăng Trưởng Toàn Farm (Farm History Aggregation)
- **Tránh nhân đôi số liệu**: Do trong 1 ngày có thể có nhiều snapshot (chạy sáng, đối soát trưa, nuôi tối), câu query lịch sử ngày BẮT BUỘC phải gom nhóm theo `(substr(timestamp, 1, 10), username)` với `rn = 1` trước khi tính `SUM()`:
  ```sql
  WITH DayUser AS (
      SELECT substr(timestamp, 1, 10) as dt, username, follower, following, heart, video, status,
             ROW_NUMBER() OVER (PARTITION BY substr(timestamp, 1, 10), username ORDER BY timestamp DESC) as rn
      FROM snapshots
      WHERE status != 'ERROR'
  )
  SELECT dt, count(username) as total_users, sum(follower), sum(following), sum(heart)
  FROM DayUser WHERE rn = 1 GROUP BY dt ORDER BY dt ASC
  ```
- **Làm mịn ngày hiện tại (Day Smoothing)**: Nếu ngày hiện tại chỉ mới có số lượng nick quét ít (< 50% ngày trước, ví dụ sau 0h đêm), tự động đồng bộ giá trị ngày đó với `summary` từ `get_farm_data()` để biểu đồ không bị gãy tụt dốc trước khi cron quét chính lúc 07:00 hoàn thành.

## 5. Kỷ luật Điều phối Worker trên Monolith > 1.500 dòng
- Với file monolith lớn (`tiktok_dashboard.py` ~ 1.900 dòng):
  * CẤM worker chạy `search_files` diện rộng hoặc đọc toàn bộ file -> chắc chắn dính timeout 600s.
  * Coordinator phải trích xuất exact unique anchor (`wc -l == 1`), cấp lệnh `patch(mode="replace")` đóng với exact string.
  * Kèm chỉ thị fail-fast: Nếu sau 3 turns không patch được thì dừng ngay, hoàn tất trong <= 8 calls.

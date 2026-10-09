# Nguyên Tắc Thiết Kế Delta: Theo Dõi Dashboard vs Đối Soát Tác Vụ

## 1. Bản Chất Hai Mục Đích Theo Dõi Khác Nhau

Trong hệ thống vận hành Phone Farm (với hàng nghìn tài khoản và cơ sở dữ liệu `tiktok_tracker.db`), số liệu biến động ($\Delta$) phục vụ hai mục đích hoàn toàn khác biệt:

| Tiêu chí | 1. Web Dashboard Hàng Ngày (`:1905`) | 2. Watchdog Đối Soát Tác Vụ (Follow / Avatar) |
| :--- | :--- | :--- |
| **Mục đích** | Theo dõi tăng trưởng toàn farm theo chu kỳ ngày/24h. | Kiểm tra tỷ lệ thành công của một đợt chạy script (batch/session). |
| **Đối tượng** | Toàn bộ nick trong farm (~1.000+ nick). | Danh sách nick vừa tham gia chạy tác vụ (~15–30 nick). |
| **Baseline đối chiếu** | **Mốc chốt cố định của ngày hôm trước** (`timestamp < current_day_start`). | **Mốc bắt đầu phiên** (`timestamp <= session_start_iso`) hoặc snapshot liền kề trước khi chạy. |
| **Tần suất hiển thị** | Cố định, không đổi đột ngột giữa các đợt cào lẻ trong ngày. | Tính tức thời ngay sau khi script hoàn thành để báo cáo Telegram. |

---

## 2. Bẫy Lệch Baseline Dashboard (`rn = 1` vs `rn = 2`)

### Hiện tượng:
- Sáng sớm (07:00), cron chạy quét toàn farm (`daily-tiktok-farm-tracker`), so với tối hôm trước thấy tim tăng mạnh (`+514`).
- Sau đó, có một tác vụ quét bù hoặc rescan lúc 07:33 (chỉ cách 33 phút).
- Người dùng vào Dashboard thấy lượt tim từ `+514` đột ngột tụt về `+1`.

### Nguyên nhân:
Nếu Dashboard truy vấn SQLite bằng cặp snapshot liền kề:
```sql
WITH Ranked AS (
    SELECT ..., ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC) as rn
    FROM snapshots
)
SELECT ... FROM Ranked r1 LEFT JOIN Ranked r2 ON r1.username = r2.username AND r2.rn = 2
```
Thì khi có bất kỳ lần quét mới nào trong ngày, `r2` bị dịch thành lần quét vừa xong. Khoảng cách giữa 2 lần quét chỉ 15–30 phút nên hầu hết nick không có biến động, làm mất hoàn toàn bức tranh tăng trưởng 24h.

### Chuẩn hóa Query Dashboard:
```sql
-- Lấy ngày mới nhất max_dt và kiểm tra xem có ngày hôm trước (< max_dt) không
-- Nếu có ngày trước: r2 lấy snapshot mới nhất trước ngày max_dt (mốc chốt cuối ngày cũ)
WITH LatestCurr AS (
    SELECT ..., ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC) as rn
    FROM snapshots WHERE substr(timestamp, 1, 10) = ?
),
LatestPrev AS (
    SELECT ..., ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC) as rn
    FROM snapshots WHERE substr(timestamp, 1, 10) < ?
)
SELECT ...
FROM LatestCurr r1
LEFT JOIN LatestPrev r2 ON r1.username = r2.username AND r2.rn = 1
```

---

## 3. Cơ Chế Đối Soát Tác Vụ Cụ Thể (Follow & Upload Avatar)

Khác với Dashboard, việc đối soát script đòi hỏi bắt đúng biến động sinh ra bởi phiên chạy:

1. **Đối soát Follow chéo (`feed_session_watchdog.py`):**
   - Chỉ cào targeted các nick vừa chạy follow (`--usernames ...`).
   - Lấy `baseline_row` neo theo `session_start_iso` (giờ mở phiên nuôi).
   - Công thức: $\Delta Following_{\text{thật}} = Following_{\text{latest}} - Following_{\text{baseline}}$.
   - Mục đích: Đối chiếu số lượt follow script báo cáo với số lượt server TikTok thực tế ghi nhận (phát hiện shadow drop / silent action block).

2. **Đối soát Upload Avatar (`post_evening_avatar_watchdog.py`):**
   - Lọc danh sách nick chưa có avatar (`has_avatar == 0`).
   - Sau khi script chạy upload xong trên thiết bị, kích hoạt rescan targeted.
   - Kiểm tra `has_avatar == 1` và `avatar_thumb` mới trong snapshot tiếp theo để xác nhận avatar đã lên thật trên server.

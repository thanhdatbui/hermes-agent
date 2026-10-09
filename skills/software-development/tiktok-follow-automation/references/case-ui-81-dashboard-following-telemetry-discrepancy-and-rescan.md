# Case UI-81: Giải Thích & Xử Lý Lệch Dữ Liệu Dashboard Giữa Follow Nội Bộ (+364) vs Tổng Tăng Web (+208)

> 📌 **Bối cảnh (2026-10-01)**: User gửi ảnh chụp màn hình TikTok Farm Dashboard với thắc mắc: *"Ủa gì lệch dữ liệu kinh v"*.
> Thẻ `TỔNG ĐÃ FOLLOW (FOLLOWING)` hiển thị: `14,349 (+208)` kèm chú thích `🔗 Nội bộ: +364 | 📈 Tổng tăng: +208`.
> Nhìn bề ngoài có vẻ mâu thuẫn phi lý: Tăng trưởng follow nội bộ (+364) là tập con mà lại lớn hơn tổng tăng trưởng follow (+208), làm dấy lên nghi vấn mất 156 lượt follow hoặc tài khoản bị nhả follow hàng loạt.

---

## 1. Bản Chất Kỹ Thuật Của Sự Lệch Pha (Mismatched Cadence & Telemetry Sources)

Dashboard (`D:/Taadaa/tools/tiktok_dashboard.py`) hiển thị 2 chỉ số follow bắt nguồn từ 2 hệ thống đo lường hoàn toàn độc lập với chu kỳ cập nhật khác nhau:

| Tiêu chí | 🔗 Số liệu "Nội bộ: +364" | 📈 Số liệu "Tổng tăng: +208" |
| :--- | :--- | :--- |
| **Nguồn dữ liệu** | Bảng `session_action_stats` & `daily_account_actions` trong `tiktok_tracker.db`. | Bảng `snapshots` trong `tiktok_tracker.db` (so sánh snapshot mới nhất hôm nay vs snapshot ngày hôm qua). |
| **Phương pháp đo** | **Real-time Telemetry từ App Android**: Ghi nhận trực tiếp sự kiện tap nút Follow thành công của bot trên thiết bị thật trong các phiên nuôi feed của ngày. | **Web Scraping từ TikTok Web Profile**: Cào HTML công khai từ `https://www.tiktok.com/@username` qua proxy pool để lấy `followingCount`. |
| **Chu kỳ cập nhật** | **Cập nhật tức thì** sau mỗi phiên nuôi (`feed_session_watchdog.py`). Hôm nay: Ca 1 P1 (+53), Ca 1 P2 (+91), Ca 2 P1 (+120), Ca 2 P2 (+100) $\rightarrow$ Tổng tích lũy 364 lượt. | **Quét toàn farm chỉ 1 lần/ngày** vào lúc 07:00 sáng (`cron_tiktok_daily_tracker.py`). Trong ngày, watchdog chỉ cào rescan một tập rất nhỏ các nick thuộc phiên hiện tại. |
| **Độ trễ phản ánh** | 0 giây (ngay khi bot bấm xong và ghi log). | Chậm từ vài giờ đến cả ngày (phụ thuộc vào thời điểm rescan) + độ trễ bộ đệm CDN (Edge Cache) của TikTok Web. |

---

## 2. Nguyên Nhân Cốt Lõi Khiến Số Liệu Lệch

1. **Tập Nick Chưa Được Rescan Kể Từ Sáng:**
   - Trong 22 tài khoản thực hiện follow hôm nay (tổng 364 lượt), có **10 nick chủ lực với 144 lượt follow** (ví dụ: `@thanh.truc0366` +21, `@hng.th.v713` +20, `@.m.hn6` +18, `@thy.dung1828` +17, `@linhtrinh446` +17...) **chưa hề được cào lại snapshot kể từ 09:10 sáng**!
   - Vì bảng `snapshots` của các nick này vẫn đang mang số liệu cũ của phiên sáng, phép tính `(current_following - prev_following)` trên Dashboard ra `diff = 0` thay vì ghi nhận số lượt follow mới của ca chiều.
2. **Độ Trễ Phổ Biến Của TikTok Web (CDN Cache Delay):**
   - Kể cả khi bot đã bấm Follow thành công trên app Android, trang profile công khai trên web TikTok (`tiktok.com/@username`) vẫn có thể hoãn cập nhật bộ đếm `followingCount` trong khoảng 15-60 phút tùy thuộc vào cụm cache server.
3. **Hiện Tượng Trùng Lặp Nick Khi Backfill Excel Gây Drift:**
   - Khi backfill tài khoản cũ (như Máy 36 `@cyennffqko8`), nếu không dọn dẹp triệt để dòng tàn dư trên máy từng bị ký sinh (Máy 76), `excel_preflight_validator.py` sẽ chặn sync runtime, làm trì hoãn đồng bộ giữa safe workbook và database tracking.

---

## 3. Quy Trình Chẩn Đoán & Khắc Phục (Diagnostic & Recovery Playbook)

### Bước 1: Đối soát nhanh chênh lệch giữa 2 bảng SQLite
Chạy script kiểm tra số follow đã ghi nhận thực tế vs số follow đã cào web:
```python
import sqlite3
con = sqlite3.connect("D:/Taadaa/data/tiktok_tracker.db")
cur = con.cursor()

# 1. Tổng follow nội bộ từ máy thật hôm nay
cur.execute("SELECT SUM(internal_follows) FROM session_action_stats WHERE target_date = date('now')")
print("Thực tế bấm trên máy:", cur.fetchone()[0])

# 2. Tìm các nick đã bấm follow nhưng chưa rescan snapshot sau 14:00
cur.execute("""
    SELECT d.username, d.internal_follows, MAX(s.timestamp)
    FROM daily_account_actions d
    LEFT JOIN snapshots s ON LOWER(d.username) = LOWER(s.username) AND s.status != 'ERROR'
    WHERE d.target_date = date('now') AND d.internal_follows > 0
    GROUP BY d.username
    HAVING MAX(s.timestamp) < datetime('now', '-2 hours')
""")
stale_snaps = cur.fetchall()
print(f"Số nick cần rescan ({len(stale_snaps)} nick):", [r[0] for r in stale_snaps])
```

### Bước 2: Kích hoạt Rescan Mục Tiêu (Targeted Rescan)
Không cần quét lại toàn bộ 1,280 nick toàn farm (tránh nghẽn proxy và tốn thời gian), chỉ bắn lệnh quét tập trung đúng các nick hoạt động hôm nay:
```bash
python D:/Taadaa/tools/tiktok_account_tracker.py \
    --usernames <nick1> <nick2> ... \
    --workers 10 \
    --db D:/Taadaa/data/tiktok_tracker.db \
    --no-export
```

### Bước 3: Xác minh Dashboard Cập Nhật
- Sau khi rescan xong, mở lại `http://localhost:8080` (hoặc refresh dashboard).
- Số liệu `📈 Tổng tăng` sẽ nhảy lên tiệm cận với `🔗 Nội bộ: +364` (chênh lệch nhỏ còn lại nếu có là do một số lượt follow đang trong thời gian trễ cache CDN của TikTok).

---

## 4. Kỷ Luật Vận Hành Khi Báo Cáo User
- Khi User thắc mắc về độ lệch dữ liệu trên Dashboard:
  1. Giải thích ngay bằng ngôn ngữ trực diện: **"Nội bộ là đo realtime trên máy thật, Tổng tăng là cào từ web TikTok định kỳ (chưa quét lại snapshot ca trưa/chiều)"**.
  2. Báo cáo cụ thể: Bao nhiêu nick chưa được quét lại sau ca nuôi, tổng số follow đang chờ phản ánh.
  3. Đề xuất hoặc thực hiện ngay lệnh rescan tập trung để đồng bộ số liệu web với thực tế thiết bị.

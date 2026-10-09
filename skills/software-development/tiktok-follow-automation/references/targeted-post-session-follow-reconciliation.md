# Kiến Trúc Đối Soát Following Sau Phiên (Targeted Post-Session Follow Reconciliation)

## 1. Bối cảnh & Bài học thực chiến
- **Sự cố nhận thức**: Nhầm lẫn giữa việc cào toàn farm (627+ nick) với việc cào đối soát sau phiên (chỉ 15–30 nick chạy follow). Cào toàn farm định kỳ vào 07:00 sáng, còn sau mỗi phiên nuôi nick chỉ cần cào targeted danh sách máy tham gia phiên đó.
- **Tốc độ & Tải proxy**: Quét 15–30 nick qua pool 67 proxy với 10 workers chỉ mất 15–25 giây, hoàn toàn an toàn và không gây nghẽn proxy hay rate-limit.
- **Tại sao cần đối soát 2 tầng**:
  1. **Tầng 1 (In-App UI Path B)**: Bắt lỗi nhả follow ngay trên giao diện máy thật (nút đổi màu đỏ trở lại sau reload).
  2. **Tầng 2 (Post-Session Scrape Delta)**: Bắt lỗi "Silent Action Block" phía server TikTok — app trên điện thoại hiển thị "Đang theo dõi" nhưng máy chủ TikTok âm thầm drop request, dẫn đến số Following trên profile thực tế không tăng.

## 2. Quy trình đối soát chuẩn (Pipeline)

```
[Máy Thật Chạy Follow]
       │
       ▼
Ghi nhận `follow_result.json` (Số follow theo UI)
       │
       ▼
[Phiên Kết Thúc -> Watchdog Phát Hiện]
       │
       ▼
Lọc danh sách máy có follow: `active_machines = [m for m, res in follow_results if res.followed_count > 0]`
       │
       ▼
Gọi cào Targeted:
`python D:/Taadaa/tools/tiktok_account_tracker.py --machines m1 m2 ... --workers 10`
       │
       ▼
Ghi snapshot mới vào SQLite: `D:/Taadaa/data/tiktok_tracker.db`
       │
       ▼
Tính Delta Following:
`Delta = Following_Snapshot_Latest - Following_Snapshot_Prev`
       │
       ▼
[Báo Cáo Telegram & Web Dashboard]
- Telegram: `Script báo X | Cào TikTok tăng thật: +Y (Lệch ngầm: -Z)`
- Web Dashboard (port 1905): Tab `👥 BXH Following` hiển thị đúng biến động.
```

## 3. Lệnh vận hành & Debug O(1)

- Chạy cào test targeted theo máy:
  ```bash
  python D:/Taadaa/tools/tiktok_account_tracker.py --machines 3 8 10 --workers 5
  ```
- Kiểm tra dữ liệu delta following trong SQLite:
  ```bash
  python -c "
  import sqlite3
  conn = sqlite3.connect('D:/Taadaa/data/tiktok_tracker.db')
  cur = conn.cursor()
  cur.execute('''
      WITH Ranked AS (
          SELECT username, following, timestamp,
                 ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC) as rn
          FROM snapshots
      )
      SELECT r1.username, r1.following, r2.following, (r1.following - r2.following) as delta
      FROM Ranked r1
      LEFT JOIN Ranked r2 ON r1.username = r2.username AND r2.rn = 2
      WHERE r1.rn = 1 AND (r1.following - r2.following) != 0
  ''')
  for row in cur.fetchall():
      print(row)
  "
  ```

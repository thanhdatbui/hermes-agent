# Follow Watchdog Web Reconcile Window Lag & Empty Target Pitfalls

## 1. Hiện Tượng Snapshot Crawler Hoàn Tất Trễ Hơn Buffer Ca (False Zero Web Delta)

### Hiện Tượng
Watchdog đối soát TikTok Web (`reconcile_cluster_following`) báo cáo:
`+ Đối soát TikTok Web (+0 Following thật | Lệch -N so với script báo N)`
Các máy đều bị báo `script N lượt - web 0 lượt - lệch (-N)`.

### Cơ Chế & Nguyên Nhân Gốc (Root Cause)
1. **Window Query Chặt Chẽ:** Ca chạy (ví dụ Ca 3 Phiên 1) có khung cố định `18:00 - 20:00`.
   Hàm đối soát tính `query_end_iso = buffer_reconcile_iso(session_end_iso, 10)` ➔ `20:10:00`.
2. **Độ Trễ Snapshot Crawler:** Crawler snapshot cào web chạy sau khi phiên lướt/follow hoàn tất, có thể ghi snapshot vào DB `tiktok_tracker.db` lúc `20:15 - 20:25`.
3. **Sụp Đổ Cặp Snapshot (Same Snapshot Collapse):**
   - Query `latest`: `WHERE timestamp <= '20:10:00'` ➔ Không khớp snapshot mới lúc 20:15+, mà lùi về snapshot sáng hôm đó (`07:03:58`).
   - Query `baseline`: `WHERE timestamp <= '18:00:00'` ➔ Cũng khớp chính snapshot sáng (`07:03:58`).
   - `latest_fl - prev_fl = 0 - 0 = 0` ➔ Watchdog kết luận web tăng 0 lượt, tạo ra cảnh báo lệch âm ảo (`lệch -N`).

### Quy Trình Đối Soát Kỹ Thuật (O(1) Verification)
Trước khi kết luận TikTok nhả follow hay nick bị shadowban, BẮT BUỘC query SQLite trực tiếp để kiểm tra timestamp thực tế của các snapshot gần nhất:
```python
import sqlite3
conn = sqlite3.connect("file:D:/Taadaa/data/tiktok_tracker.db?mode=ro", uri=True)
cur = conn.cursor()
cur.execute("""
    SELECT timestamp, following, follower
    FROM snapshots
    WHERE LOWER(username) = LOWER(?)
    ORDER BY timestamp DESC LIMIT 3
""", (username,))
rows = cur.fetchall()
# So sánh timestamp snapshot mới nhất với session_end_iso để phát hiện độ trễ crawler
```

---

## 2. Lỗi Nhầm Lẫn Câu Chữ Khi Toàn Cụm Bỏ Qua Follow (False Missing Username)

### Hiện Tượng
Watchdog xuất dòng:
`+ Đối soát TikTok Web: Không tìm thấy username trong workbook cho 75 máy follow`
Dù trên thực tế 75 máy đó là diện **Bỏ qua / Chưa đủ điều kiện (0 follow chéo)**.

### Cơ Chế Kỹ Thuật
1. `target_machines` gom cả `{str(m) for m in all_follows.keys()}` (bao gồm tất cả máy có record trạng thái trong lượt chạy, kể cả khi 0 lượt follow).
2. Khi lặp qua từng máy:
   ```python
   if cnt <= 0 and natural_cnt <= 0 and not (failed or is_timeout_or_err):
       continue
   ```
   Do cả 75 máy đều `cnt == 0`, chúng đều bị `continue` ➔ Danh sách `m_to_user` rỗng.
3. Nhánh fallback:
   ```python
   if not m_to_user:
       if target_machines:
           return [f"  + Đối soát TikTok Web: Không tìm thấy username trong workbook cho {len(target_machines)} máy follow"]
   ```
   Dẫn đến câu thông báo sai ngữ cảnh, làm người vận hành hoang mang tưởng 75 máy đi follow bị thất lạc thông tin tài khoản.

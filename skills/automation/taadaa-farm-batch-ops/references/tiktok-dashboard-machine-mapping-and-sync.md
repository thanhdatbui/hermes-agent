# Đồng bộ số máy cho tài khoản TikTok & Dashboard SQLite (farm_account_info)

## 1. Bản chất kiến trúc Dashboard & Mapping số máy
- Dashboard web tại port 1905 (`D:/Taadaa/tools/tiktok_dashboard.py`) lấy thông tin số máy (`Mxx`) và cụm máy (`kibe` / `admin`) thông qua câu truy vấn SQL:
  ```sql
  LEFT JOIN farm_account_info f ON r1.username = f.username
  ```
- Bảng `farm_account_info` trong SQLite `D:/Taadaa/data/tiktok_tracker.db` có schema:
  - `username` (TEXT PRIMARY KEY)
  - `may` (INTEGER)
  - `tik` (INTEGER)
  - `host_id` (TEXT: `'kibe'` nếu máy 1-80, `'admin'` nếu máy 201-280)
  - `updated_at` (TEXT)
- **Triệu chứng lỗi**: Khi nick trên Dashboard hiển thị trạng thái `LIVE`, có follower / tim nhưng **KHÔNG CÓ BADGE SỐ MÁY** (hoặc lọc theo cụm bị mất nick), nguyên nhân 100% là do nick đó chưa có bản ghi trong bảng `farm_account_info`.

---

## 2. Quy trình kiểm tra O(1) khi phát hiện nick thiếu số máy

1. **Kiểm tra trạng thái trong SQLite**:
   ```python
   import sqlite3
   conn = sqlite3.connect("D:/Taadaa/data/tiktok_tracker.db")
   c = conn.cursor()
   # Kiểm tra snapshots vs farm_account_info
   c.execute("SELECT * FROM farm_account_info WHERE username = ?", (username,))
   print("farm_account_info:", c.fetchall())

   # Thống kê số nick LIVE chưa có số máy
   c.execute("""
       WITH Latest AS (
           SELECT username, status, ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC) as rn
           FROM snapshots
       )
       SELECT COUNT(*) FROM Latest
       WHERE rn = 1 AND status = 'LIVE' AND username NOT IN (SELECT username FROM farm_account_info)
   """)
   print("Nick LIVE thiếu số máy:", c.fetchone()[0])
   conn.close()
   ```

2. **Truy tìm nick trong Excel nguồn**:
   - Quét tìm trong các file `D:/OneDrive/TaadaaData/admin/Tik*.xlsx`, `D:/OneDrive/TaadaaData/kibe/Tik*.xlsx`, `taikhoan_run_safe_combined.xlsx` hoặc bản backup `taikhoan_dat_v2_updated`.
   - Xác định chính xác: Máy nào, Slot Tik mấy, Host nào.

---

## 3. Quy trình gán slot và đồng bộ toàn diện vào SQLite

### Bước 1: Gán vào slot trống trên file Excel (Giữ nguyên cấu trúc dòng)
- Tuyệt đối không xóa dòng hay chèn dòng (giữ vững quy tắc 8 slot/máy).
- Ghi username vào cột C (ID) của dòng Máy tương ứng trên file `Tik<N>.xlsx`.

### Bước 2: Đồng bộ vào bảng `farm_account_info`
- Backup `D:/Taadaa/data/tiktok_tracker.db` trước khi cập nhật.
- Chạy batch upsert nạp dữ liệu từ các file `Tik*.xlsx` của cả 2 cụm:
  ```python
  import openpyxl, sqlite3, glob, re, os

  conn = sqlite3.connect("D:/Taadaa/data/tiktok_tracker.db")
  c = conn.cursor()

  sources = []
  for p in glob.glob("D:/OneDrive/TaadaaData/kibe/Tik*.xlsx"):
      m = re.search(r"[Tt]ik(\d+)", os.path.basename(p))
      if m: sources.append((p, int(m.group(1)), "kibe"))
  for p in glob.glob("D:/OneDrive/TaadaaData/admin/Tik*.xlsx"):
      if "bak" in p.lower(): continue
      m = re.search(r"[Tt]ik(\d+)", os.path.basename(p))
      if m: sources.append((p, int(m.group(1)), "admin"))

  for path, tik, host in sources:
      wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
      ws = wb.active
      for row in ws.iter_rows(min_row=2, values_only=True):
          if not row: continue
          may_val, id_val = row[0], (row[2] if len(row) > 2 else None)
          if not id_val or str(id_val).strip().lower() in ("none", "missing_id", ""):
              continue
          uname = str(id_val).strip().lstrip("@")
          try:
              may_int = int(may_val)
              c.execute("""INSERT OR REPLACE INTO farm_account_info (username, may, tik, host_id, updated_at)
                           VALUES (?, ?, ?, ?, datetime('now', 'localtime'))""",
                        (uname, may_int, tik, host))
          except Exception:
              continue
      wb.close()

  conn.commit()
  conn.close()
  ```

### Bước 3: Nghiệm thu Visual Evidence (Gate 6)
- Điều hướng browser tới `http://127.0.0.1:1905/`.
- Search username trên ô tìm kiếm của Dashboard.
- Chụp ảnh màn hình nghiệm thu (`browser_vision`) xác nhận badge máy (màu xanh cho `kibe`, màu tím cho `admin`) đã hiển thị chuẩn xác và gửi ảnh `MEDIA:<path_anh>`.

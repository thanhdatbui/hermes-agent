# Điều tra Sự Cố Nick LIVE Mất Badge Số Máy trên Dashboard & OneDrive Dehydration

## Bối Cảnh & Hiện Tượng (2026-09-22)
- Trên TikTok Farm Web Dashboard (`http://localhost:1905`), người dùng phát hiện nick `@anan36014` (#2 BXH Tim, LIVE, 55 tim, 1 video) cùng hàng loạt nick khác (`@cout13110`, `@haibich156`, `@huynhat1035`) hoàn toàn không hiển thị badge số máy (`M{may}` như M39, M247...).
- Đồng thời, lượt quét Daily Tracker 07:01 sáng chỉ nạp được 627 nick Kibe (1..80), bỏ sót toàn bộ cụm Admin (Máy 201..280).

---

## Nguyên Nhân Gốc Rễ (Root Cause Analysis)

### 1. Bảng `farm_account_info` là bảng tĩnh, thiếu Auto-Sync
- Query hiển thị của Dashboard (`tiktok_dashboard.py`):
  ```sql
  LEFT JOIN farm_account_info f ON r1.username = f.username
  ```
- Bảng `farm_account_info` trong SQLite `tiktok_tracker.db` chỉ được khởi tạo tĩnh từ đợt chạy script 18/09 - 20/09.
- Không có trigger hoặc cronjob định kỳ đồng bộ từ danh bạ hợp nhất `taikhoan_run_safe_combined.xlsx` vào `farm_account_info`.
- Hậu quả: Khi có nick mới reg hoặc đổi slot, nick có trong `snapshots` (crawler quét live từ TikTok profile) nhưng không có trong `farm_account_info` (`f.may IS NULL`), dẫn đến Dashboard không render badge `M{may}` (136 nick LIVE bị ảnh hưởng).

### 2. Sự cố "Nick Lạc" `@anan36014` sau khi Restore Folder 2
- Nick `@anan36014` thực chất thuộc **Máy 218** (Admin), reg thành công ngày 16/09/2026 với mail `schappachude360@hotmail.com` (UID `7687316790196028432`).
- Vào ngày 16/09, tool reg ghi nhầm nick này vào dòng Folder 2 và Folder 8 của Máy 218 trong `taikhoan_dat_v2_updated .xlsx`.
- Sáng 21/09, khi chạy script khôi phục 69 nick Folder 2 bị ghi đè từ backup cũ `bak_final.xlsx`, 2 dòng trên được trả về nick cũ (`bongbong10045` và `maiquangthinh783`).
- Do chưa dời `@anan36014` sang các slot còn trống của Máy 218 (Tik 4, 5, 6), nick bị tách khỏi danh bạ Excel Admin và không bao giờ được sync vào `farm_account_info`.

### 3. OneDrive Files On-Demand Dehydration làm sập `load_farm_accounts()`
- File `D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx` bị OneDrive đưa về trạng thái Cloud-Only / Dehydrated (`attrib A O`, attribute `0x401620`).
- Khi Python (`openpyxl.load_workbook`) cố đọc file này, Windows trả về lỗi:
  ```text
  OSError: [Errno 22] Invalid argument / zipfile.BadZipFile: File is not a zip file
  ```
- Trong `tiktok_account_tracker.py`, hàm `load_farm_accounts()`:
  ```python
  for path in target_paths:
      if not os.path.exists(path):
          continue
      try:
          wb = openpyxl.load_workbook(path, data_only=True)
          ws = wb.active
      except Exception:
          continue
  ```
  `os.path.exists()` trả về `True`, nhưng `openpyxl` văng `OSError 22`, bị khối `except Exception: continue` nuốt chửng mà không log telemetry, dẫn đến âm thầm bỏ qua toàn bộ 80 máy của cụm Admin.

---

## Quy Trình Khắc Phục & Chuẩn Hóa

### Bước 1: Khóa file luôn giữ trên máy (Pin OneDrive File)
Chạy lệnh PowerShell / cmd để pin file không bị OneDrive dehydrate:
```cmd
attrib -u +p "D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx"
attrib -u +p /s /d "D:\OneDrive\TaadaaData\*.xlsx"
```

### Bước 2: Bổ sung Telemetry & Pin Check trong `load_farm_accounts()`
Không bắt `except Exception: continue` mù quáng. Bắt buộc in warning hoặc raise alert khi file tồn tại nhưng không mở được do lỗi OS/OneDrive:
```python
try:
    wb = openpyxl.load_workbook(path, data_only=True)
except Exception as e:
    logger.error(f"[LOAD_ACCOUNTS_FAIL] Cannot open workbook {path}: {e}")
    # Nếu dính OSError 22 -> thử pin lại file qua attrib +p
```

### Bước 3: Đồng bộ tự động `farm_account_info` từ `taikhoan_run_safe_combined.xlsx`
Trước mỗi lần crawl snapshot hoặc định kỳ sau khi đồng bộ danh bạ:
```python
import sqlite3, openpyxl

conn = sqlite3.connect("D:/Taadaa/data/tiktok_tracker.db")
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS farm_account_info (
        username TEXT PRIMARY KEY,
        may INTEGER,
        tik INTEGER,
        updated_at TEXT,
        host_id TEXT DEFAULT 'kibe'
    )
""")

wb = openpyxl.load_workbook("D:/OneDrive/TaadaaData/taikhoan_run_safe_combined.xlsx", read_only=True, data_only=True)
ws = wb.active
for r in list(ws.iter_rows(values_only=True))[1:]:
    if r and len(r) >= 3 and r[0] and r[2]:
        m_int = int(r[0])
        u_str = str(r[2]).strip().lstrip("@")
        host = "admin" if m_int >= 200 else "kibe"
        c.execute("""
            INSERT OR REPLACE INTO farm_account_info (username, may, updated_at, host_id)
            VALUES (?, ?, datetime('now', 'localtime'), ?)
        """, (u_str, m_int, host))
wb.close()
conn.commit()
conn.close()
```

### Bước 4: Tái nạp nick mồ côi (`@anan36014`)
Điền `@anan36014` vào slot trống của Máy 218 (Tik 4) trên `admin/Tik4.xlsx` và `admin/taikhoan_run_safe.xlsx`, sau đó chạy lại script sync combined.

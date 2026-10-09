# GPM Profile Backup & Selective Compression Technique (2026-09-05)

## 1. Mục Đích & Bối Cảnh
Sao lưu định kỳ cơ sở dữ liệu `profile_data.db` và nén các profile GPM đang hoạt động (như các profile Farm S7 vừa đăng nhập thành công và kích hoạt 2FA) vào thư mục đồng bộ đám mây `D:\OneDrive\backup\GPM\`.

## 2. Quy Trình Chuẩn 4 Bước

### Bước 1: Sao lưu Database SQLite
Copy nguyên bản database metadata trước khi xử lý:
```python
import shutil
from pathlib import Path

src_db = Path(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db")
dst_db = Path(r"D:\OneDrive\backup\GPM\profile_data_backup_20260905.db")
shutil.copy2(src_db, dst_db)
```

### Bước 2: Truy Vấn SQLite Lọc Profile Mục Tiêu
Truy vấn các profile thuộc Group mục tiêu (`GroupId = 1`) được tạo theo đợt chạy (hậu tố `-04092026`, `-05092026` hoặc timestamp `CreatedAt`):
```sql
SELECT Id, Name, ProfilePath, CreatedAt, UpdatedAt, LastRunAt 
FROM Profiles 
WHERE GroupId = 1 
  AND (ProfilePath LIKE '%04092026%' OR ProfilePath LIKE '%05092026%')
ORDER BY CreatedAt;
```

### Bước 3: Dọn Tiến Trình Khóa Profile TRƯỚC Khi Nén (CRITICAL)
**Cạm bẫy:** Nếu có bất kỳ profile nào đang mở hoặc tiến trình `gpm_browser` bị mồ côi (chưa thoát sạch), Windows sẽ lock các file như:
- `SUNVqFew4a-05092026\lockfile`
- `Default\Network\Cookies` và `Cookies-journal`
- `Default\Sessions\Session_*`
- `Default\Local Storage\leveldb\LOCK`
- `ShaderCache\*`

Dẫn đến lỗi `[Errno 13] Permission denied` khi `zipfile` cố đọc file, làm thất thoát cookie/session trong bản backup.

**Giải pháp bắt buộc trước khi nén:** Chạy lệnh PowerShell lọc đúng tiến trình Chrome thuộc GPM để kill, bảo toàn 100% Chrome cá nhân của người dùng:
```powershell
Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | Where-Object { $_.CommandLine -match 'gpm_browser' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
```

### Bước 4: Nén Chọn Lọc (Selective Compression) Bỏ Rác Cache
Không nén nguyên khối thư mục Chromium vì chứa hàng trăm MB file tạm/cache gây phình file và tốn thời gian I/O.
- **Danh mục thư mục rác loại trừ (Junk Dirs):**
  `{'cache', 'code cache', 'crashpad', 'cachestorage', 'gpucache', 'dawngraphitecache', 'dawnwebgpucache', 'graphitedawncache', 'browsermetrics'}`
- **Dữ liệu cốt lõi bảo toàn 100%:**
  - `Default/Network/Cookies`
  - `Default/Preferences`
  - `Default/Login Data`
  - `Default/GPMSoft/` (chứa extensions & gpm_pi.dat)
  - `Local State`
  - `Default/Web Data`, `Default/IndexedDB/`

**Code mẫu nén chuẩn:**
```python
import os, zipfile
from pathlib import Path

junk_names = {'cache', 'code cache', 'crashpad', 'cachestorage', 'gpucache', 'dawngraphitecache', 'dawnwebgpucache', 'graphitedawncache', 'browsermetrics'}

with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for p_path in target_profile_paths:
        p_dir = base_profile_dir / p_path
        for root, dirs, files in os.walk(p_dir):
            rel_parts = [part.lower() for part in Path(root).relative_to(p_dir).parts]
            if any(part in junk_names for part in rel_parts):
                continue
            for file_name in files:
                file_full = os.path.join(root, file_name)
                rel_to_profile = os.path.relpath(file_full, p_dir)
                arcname = f"{p_path}/{rel_to_profile}".replace("\\", "/")
                zf.write(file_full, arcname=arcname)
```

## 3. Kiểm Tra Toàn Vẹn & Nghiệm Thu
Sau khi nén, luôn chạy kiểm tra:
```python
with zipfile.ZipFile(zip_path, "r") as zf:
    assert zf.testzip() is None, "ZIP corrupted!"
```

## 4. Dữ Liệu Thực Tế Bản Backup 2026-09-05
- **Database Backup:** `D:\OneDrive\backup\GPM\profile_data_backup_20260905.db` (1.67 MB).
- **Profile Archive:** `D:\OneDrive\backup\GPM\gpm_active_profiles_20260905.zip` (141.04 MB).
- **Số lượng profile:** 28 profile Group 1 (Farm S7 đợt 04/09 & 05/09/2026).
- **Files nén:** 9,581 files (462.73 MB uncompressed $\rightarrow$ 141.04 MB compressed).
- **Files rác bỏ qua:** 504 files (156.66 MB).
- **Thời gian nén:** ~37.5 giây.

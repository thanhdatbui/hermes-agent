# Workbook Concurrency & OneDrive Sync Resilience

## 1. Vấn đề gốc rễ (Root Cause)
Khi các tác vụ chạy ngầm định kỳ (như cron job `sync_all_tik_keywords.py`) mở và ghi đè trực tiếp lên file Excel sống trong thư mục đồng bộ OneDrive (`D:\OneDrive\TaadaaData\kibe\TikX.xlsx`) bằng lệnh trực tiếp:
```python
wb.save(str(p))
```
quá trình này gây ra các lỗi nghiêm trọng cho các tiến trình consumer đọc đồng thời (`AccountSource.read_row()` trong `Tiktok-video`):
1. **Tranh chấp khóa cấp OS / OneDrive Lock (WinError 32):** OneDrive đồng bộ file khi file đang được ghi hoặc openpyxl đang giữ file descriptor mở (`read_only=True` giữ zip handle).
2. **Đọc trúng file đang ghi dở (`BadZipFile` / rỗng):** File `.xlsx` là một file zip. Ghi trực tiếp làm file zip ở trạng thái không hoàn chỉnh trong vài chục/trăm milliseconds.
3. **Mất dữ liệu header / parse row lỗi:** Dẫn đến exception `Missing required fields: ID TikTok` hoặc `Workbook read failed`.

---

## 2. Tiêu chuẩn Ghi (Writer Contract): Bắt buộc Atomic Replacement

Mọi script/cron cập nhật workbook Tik1..Tik8 **tuyệt đối không** gọi `wb.save()` trực tiếp vào đường dẫn đích. Bắt buộc dùng `atomic_workbook_update` từ `automation_core.workbook`:

```python
from automation_core.workbook import atomic_workbook_update

def update_worker(temp_path: Path):
    wb = openpyxl.load_workbook(str(temp_path))
    # Thực hiện chỉnh sửa trên ws...
    wb.save(str(temp_path))
    wb.close()
    return True

atomic_workbook_update(
    path=target_path,
    update=update_worker,
    backup=True,
    lock_timeout=30.0,
)
```

### 2.1. Standalone Lightweight Pattern (khi không import automation_core)
Với các script tiện ích / standalone tools độc lập (ví dụ `D:/Taadaa/tools/ensure_row_accounts.py`), nếu không muốn phụ thuộc vào package `automation_core`, tối thiểu bắt buộc phải dùng cơ chế ghi `.tmp` rồi `replace`:

```python
# Atomic save: ghi vao file .tmp roi replace de tranh corrupt zip workbook
tmp_trk = TRACKING_WORKBOOK.with_suffix(".tmp.xlsx")
wb_trk.save(tmp_trk)
tmp_trk.replace(TRACKING_WORKBOOK)
```
*Lưu ý:* Luôn đặt file `.tmp` cùng thư mục/cùng ổ đĩa (`with_suffix` trên `Path` đích) để thao tác `replace` là atomic rename ở cấp filesystem OS, không bị `EXDEV` (cross-device move) và không bao giờ để lại file zip hỏng/dở dang tại file chính khi tiến trình bị ngắt đột ngột.

### Cơ chế đảm bảo an toàn của `atomic_workbook_update`:
1. **Acquire Lock Lease:** Khóa độc quyền đa tiến trình chống race condition giữa các writer.
2. **Tạo Backup tự động:** Lưu bản snapshot `.bak` trước khi chỉnh sửa.
3. **Ghi trên Tempfile:** Mọi thao tác openpyxl thực hiện trên file tạm nằm cùng filesystem (`tempfile.mkstemp(..., dir=target.parent)`).
4. **Atomic Swap (`os.replace`):** Hoán đổi file nguyên tử qua lệnh `os.replace` với backoff retry `REPLACE_RETRY_DELAYS = (0.0, 0.2, 0.5, 1.0, 2.0, 4.0, 8.0, 8.0)` để vượt qua khoảnh khắc OneDrive quét file.

---

## 3. Tiêu chuẩn Đọc (Reader Contract): Tăng Chịu Lỗi & Fallback Backup

Trong các consumer runner (như `AccountSource.read_row()`):

1. **Lock Wait Timeout:** Nâng thời gian chờ lock từ 10.0s lên 30.0s:
   ```python
   lock_wait = self._wait_for_lock(lock_file, timeout=30.0)
   ```
2. **Đọc qua Bytes Buffer (`io.BytesIO`):**
   Thay vì truyền thẳng `path` vào `openpyxl.load_workbook`, hãy đọc bytes nhanh vào memory:
   ```python
   import io
   data = self.workbook_path.read_bytes()
   buf = io.BytesIO(data)
   wb = openpyxl.load_workbook(buf, read_only=True, data_only=True)
   ```
   *Lợi ích:* Thao tác `read_bytes()` diễn ra tức thời ở mức OS, giải phóng file handle ngay lập tức, không giữ file lock làm block `os.replace` của writer.
3. **Fallback Backup (`.bak`):**
   Nếu file chính bị `BadZipFile` hoặc lỗi I/O do xung đột sync, tự động fallback sang đọc file `.bak` gần nhất:
   ```python
   bak_path = self.workbook_path.with_suffix(self.workbook_path.suffix + ".bak")
   if bak_path.exists():
       logger.warning(f"Fallback reading from backup {bak_path}")
       # Đọc từ bak_path...
   ```

---

## 4. Multi-Location Sync & Verification Checklist

### Đồng bộ các bản copy của script Writer (`sync_all_tik_keywords.py`):
Khi cập nhật `sync_all_tik_keywords.py`, bắt buộc đồng bộ đồng nhất qua cả 3 vị trí deploy trên hệ thống:
1. `C:\Users\Kibe\AppData\Local\hermes\scripts\sync_all_tik_keywords.py` (Hermes local scripts)
2. `D:\Taadaa\Hermes\deploy\hermes-home\scripts\sync_all_tik_keywords.py` (Hermes deploy source)
3. `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\sync_all_tik_keywords.py` (OneDrive shared cron runner)

### Verification Commands:
- **Test Reader AccountSource với thiết bị thực tế/mẫu:**
  ```bash
  python -c "import sys; sys.path.insert(0, r'D:\Taadaa\Tiktok-video\scripts'); from tiktok_workflow.account_source import AccountSource; src = AccountSource(r'D:\OneDrive\TaadaaData\kibe\Tik5.xlsx', device_id='9885e64c484c544d32'); res = src.read_row(); assert res is not None and res['ID TikTok'] == 'alemafxjvxw'; print('PASS ACCOUNT_SOURCE TEST')"
  ```
- **Test Writer Run không lỗi:**
  ```bash
  python C:\Users\Kibe\AppData\Local\hermes\scripts\sync_all_tik_keywords.py --silent
  ```


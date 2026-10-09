# Khắc phục lỗi Excel Process Lock (Errno 13) & OneDrive Reversion khi sửa Workbook Tik

## 1. Triệu chứng & Nguyên nhân
- Khi agent chạy script Python đọc/ghi file `Tik{N}.xlsx` hoặc `taikhoan_dat_v2_updated .xlsx` nằm trong thư mục `D:/OneDrive/TaadaaData/`:
  - `PermissionError: [Errno 13] Permission denied: 'D:/OneDrive/TaadaaData/kibe/Tik6.xlsx'`
  - Sau khi script Python sửa workbook, kiểm tra lại thấy dữ liệu bị **quay về trạng thái cũ (reverted)** do ứng dụng Excel trên Windows đang mở file và lưu đè lại, hoặc OneDrive sync conflict.
- **Nguyên nhân gốc rễ**: 
  - Tiến trình `EXCEL.EXE` trên Windows đang giữ file lock độc quyền (exclusive lock).
  - Ghi đè trực tiếp qua `wb.save(path)` khi file đang mở hoặc đang sync bị chặn hoặc bị ghi đè ngược.

---

## 2. Quy trình xử lý chuẩn (O(1) Unlocking & Atomic Save)

### Bước 1: Kiểm tra và đóng tiến trình Excel đang khóa file
```bash
# Kiểm tra PID của EXCEL.EXE đang chạy
powershell -NoProfile -Command "Get-Process excel, excel* -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, MainWindowTitle"

# Đóng tiến trình Excel gây lock (ví dụ PID 137496)
taskkill /PID <PID>
```

### Bước 2: Lưu file theo chuẩn Atomic Replace (.tmp -> replace)
Luôn lưu ra file tạm rồi `os.replace` để tránh xung đột ghi đè giữa chừng:
```python
import openpyxl, os

file_path = "D:/OneDrive/TaadaaData/kibe/Tik1.xlsx"
wb = openpyxl.load_workbook(file_path)
ws = wb.active

# Cập nhật ô dữ liệu cần thiết
# ...

# Lưu atomic
tmp_path = file_path + ".tmp"
wb.save(tmp_path)
os.replace(tmp_path, file_path)
```

### Bước 3: Reopen Data-Only Verify
Bắt buộc mở lại file ở chế độ `data_only=True` để kiểm tra giá trị thực tế sau khi lưu:
```python
wb_v = openpyxl.load_workbook(file_path, data_only=True)
ws_v = wb_v.active
# Assert lại row vừa sửa
```

---

## 3. Quy trình Audit nhanh 8 Workbook Tik (640 dòng) & Đối soát DB

Dùng script Python O(1) quét toàn bộ 8 file `Tik1.xlsx` -> `Tik8.xlsx`:
1. **Kiểm tra 5 Invariant**:
   - `ID` trống / `None`
   - Cột `Kiểm Tra Dữ Liệu` != `OK` (ví dụ `MISSING_ID`, `ERROR`)
   - `device ID` trống
   - Trùng lặp `Máy` trong cùng workbook
   - Trùng lặp `ID` chéo giữa 8 workbook
2. **Đối soát Source of Truth**:
   - Tra cứu `taikhoan_dat_v2_updated .xlsx` theo `Máy` và `Folder Video`.
   - Tra cứu `farm_account_info` trong `D:/Taadaa/data/tiktok_tracker.db`.
   - Nếu slot đã có nick: Cập nhật `ID`, `Keyword`, `Hashtag Pool`, `Kiểm Tra Dữ Liệu = 'OK'`, giữ nguyên `Video Đã Đăng`.
   - Nếu slot thực sự chưa có nick trên master: Báo cáo rõ slot trống để user cấp acc/reg mới.

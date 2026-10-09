# Chẩn đoán & Xử lý Khóa File Excel (Process Lock) và Bẫy Ghi Đè OneDrive (Cloud Reversion)

## 1. Hiện tượng & Vấn đề thực tế (Field Incident 2026-09-25)
Trong quá trình vận hành Phone Farm và audit kho file dữ liệu `Tik1..Tik8.xlsx` tại `D:/OneDrive/TaadaaData/kibe/`:

1. **Khóa File Độc Quyền (Win32 PermissionError [Errno 13])**:
   - Khi chạy script Python đọc/ghi workbook:
     ```text
     PermissionError: [Errno 13] Permission denied: 'D:/OneDrive/TaadaaData/kibe/Tik6.xlsx'
     ```
   - Nguyên nhân: Tiến trình `EXCEL.EXE` (cửa sổ người dùng mở xem hoặc tiến trình orphaned chạy ngầm) đang giữ handle độc quyền tới file `.xlsx` trên Windows. Bất kỳ lệnh `openpyxl.load_workbook()` nào cũng sẽ crash ngay lập tức.

2. **Bẫy Ghi Đè Ngầm OneDrive (Silent Cloud Reversion)**:
   - File nằm trong thư mục đồng bộ OneDrive (`D:/OneDrive/...`).
   - Khi script thực hiện sửa dữ liệu (kể cả dùng `os.replace` atomic save), OneDrive client có thể phát hiện xung đột sync hoặc đồng bộ ngược từ cloud xuống, làm mất thay đổi vừa ghi (revert về trạng thái cũ như `MISSING_ID`), hoặc tạo ra các file rác xung đột ngầm dạng `.Tik1.yascxce4.xlsx`.

3. **Hội chứng Kênh Bỏ Quên (Dark Channel Syndrome do Blank ID)**:
   - Khi một dòng máy trong file Tik bị mất `ID` (`None`) hoặc mang trạng thái `MISSING_ID`, upload runner sẽ tự động skip máy đó để tránh crash batch.
   - Hậu quả: Kênh TikTok ngừng đăng clip suốt nhiều tuần/tháng (ví dụ `@ngomai.ly` dừng từ tháng 8 đến cuối tháng 9) dù video render sẵn trong folder vẫn còn hàng chục clip.
   - Cạm bẫy đối soát: Dòng có thể bị lỗi không nhất quán — ví dụ `tik3.xlsx` dòng 63 (Máy 62) có `ID: None` nhưng cột `Kiểm Tra Dữ Liệu` lại ghi `'OK'`. Do đó, kiểm tra audit **bắt buộc** phải check trực tiếp `uid is None or str(uid).strip() == ''`, không được chỉ lọc theo cột trạng thái.

---

## 2. Quy trình Xử lý Khóa File Excel (Process Lock Triage)

### Bước 1: Kiểm tra tiến trình Excel đang mở file
```powershell
powershell -NoProfile -Command "Get-Process excel, excel* -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, MainWindowTitle, StartTime"
```
Output sẽ cho biết chính xác PID và tên file đang mở trên thanh tiêu đề (ví dụ: `137496 EXCEL Tik6.xlsx - Excel`).

### Bước 2: Đóng tiến trình an toàn
Khi user yêu cầu hoặc cần giải phóng file:
```cmd
taskkill /PID <PID>
```
Nếu tiến trình bị treo hoặc không phản hồi:
```cmd
taskkill /F /PID <PID>
```
Sau đó kiểm tra lại quyền truy cập file bằng openpyxl `read_only=True`.

---

## 3. Quy trình Ghi Workbook trên Thư mục OneDrive (Safe OneDrive Write)

1. **Tránh ghi trực tiếp lên file đang mở**: Luôn đảm bảo không có tiến trình Excel nào giữ file trước khi ghi.
2. **Atomic Write với .tmp cùng thư mục**:
   ```python
   import os, openpyxl

   tmp_path = file_path + '.tmp'
   wb.save(tmp_path)
   os.replace(tmp_path, file_path)
   ```
3. **Verify tính bền vững sau đồng bộ (Post-Sync Verification)**:
   - Sau khi ghi và reopen xác nhận lần 1, cần kiểm tra lại sau khi OneDrive hoàn tất sync hoặc kiểm tra thư mục có xuất hiện file conflict ẩn dạng `.<Filename>.*.xlsx` hay không.
   - Nếu OneDrive liên tục rollback thay đổi, cần tạm dừng OneDrive sync (`OneDrive.exe /pause` hoặc kiểm tra khay hệ thống) trước khi ghi đè dứt điểm.

---

## 4. Script Kiểm Tra Toàn Diện Trống ID Xuyên Suốt 8 File Tik (All-Tik ID Audit)
Chạy script O(1) kiểm tra nhanh cả 640 dòng của 8 file Tik mà không phụ thuộc vào cột trạng thái:

```python
import openpyxl, os

paths = ['Tik1.xlsx', 'Tik2.xlsx', 'tik3.xlsx', 'Tik4.xlsx', 'Tik5.xlsx', 'Tik6.xlsx', 'Tik7.xlsx', 'Tik8.xlsx']
base = 'D:/OneDrive/TaadaaData/kibe'

missing_accounts = []
for fn in paths:
    p = os.path.join(base, fn)
    if not os.path.exists(p):
        continue
    wb = openpyxl.load_workbook(p, data_only=True, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    header = [str(x).strip() if x is not None else '' for x in rows[0]]
    idx = {name: i for i, name in enumerate(header)}
    
    for rn, r in enumerate(rows[1:], 2):
        if not any(x is not None for x in r):
            continue
        m = r[idx.get('Máy', 0)]
        uid = r[idx.get('ID', 2)]
        dev = r[idx.get('device ID', 1)]
        st = r[idx.get('Kiểm Tra Dữ Liệu', 8)] if len(r) > 8 else None
        
        # Bắt cả 2 trường hợp: ID bị rỗng HOẶC trạng thái đánh dấu MISSING_ID
        if not uid or str(uid).strip() == '' or str(st).strip().upper() == 'MISSING_ID':
            missing_accounts.append({
                'file': fn,
                'row': rn,
                'may': m,
                'uid': uid,
                'device': dev,
                'status': st
            })

print(f"Tổng số tài khoản bị trống ID hoặc MISSING_ID: {len(missing_accounts)}")
for item in missing_accounts:
    print(item)
```

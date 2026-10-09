# Excel Preflight Validator & 5 Farm Invariant Rules

## Tổng quan
Khi vận hành Phone Farm và quản lý cấu hình qua Excel control plane (`Tik1..Tik8.xlsx`, `taikhoan_run_safe.xlsx`), các lỗi lệch công thức, gõ nhầm dữ liệu (vd: password/email nhảy vào cột Folder Video), hoặc trùng lặp tài khoản giữa các slot/máy sẽ phá hỏng pipeline upload và feed session.

Để ngăn chặn fail-closed hoặc crash giữa ca chạy, script `D:\Taadaa\tools\excel_preflight_validator.py` kiểm định tự động **5 Invariant Rules** trước khi dispatch batch.

## 5 Invariant Rules chuẩn

### 1. Rule 1: Slot limit per machine (Tối đa 8 tài khoản / máy)
- Mỗi máy vật lý chỉ có tối đa 8 slot tài khoản.
- Trong cùng một file `Tik{N}.xlsx`, mỗi máy chỉ xuất hiện đúng 1 lần (1 dòng cấu hình). Không được xuất hiện 2 dòng cùng số máy trong 1 file Tik.
- Tổng số tài khoản có ID hợp lệ trên 8 file Tik không được vượt quá 8 tài khoản cho cùng 1 máy.

### 2. Rule 2: No duplicate accounts (Không trùng lặp tài khoản giữa các slot / file Tik)
- Một tài khoản TikTok (dựa trên username chuẩn hóa lowercase) chỉ được phép gắn vào duy nhất 1 slot trên toàn farm.
- Không được xuất hiện ở 2 dòng khác nhau trong cùng 1 file `Tik{N}.xlsx` hoặc giữa các file khác nhau (`Tik1..Tik8.xlsx`).
- Ngoại trừ các placeholder: `None`, `null`, `MISSING_ID`, chuỗi rỗng.

### 3. Rule 3: Folder Video formula & uniqueness (Độc bản & đúng công thức Folder Video)
- Giá trị `Folder Video` (Cột 4) là mã thư mục output render trong `D:\TIKTOK-videonuoinick\<Folder Video>\`.
- **BẮT BUỘC** là số nguyên và khớp chính xác công thức toán học:
  $$\text{Folder Video} = (m - 1) \times 8 + \text{slot}$$
  *(trong đó $m$ là số máy $1..80$, và $\text{slot}$ là số thứ tự file Tik $1..8$)*.
- `Folder Video` phải độc bản trên toàn bộ farm, không bao giờ có 2 dòng trùng `Folder Video`.
- **Pitfall**: Tuyệt đối không để chuỗi ký tự lạ, password hoặc link rơi vào cột này (như sự cố dòng 31 máy 30 `tik3.xlsx` bị điền nhầm password `Susan123@Ks`).

### 4. Rule 4: Video Gốc formula & uniqueness in same Tik file (Độc bản Video Gốc trong cùng ca)
- Giá trị `video gốc` (Cột 5) là thư mục nguồn tải về trong `D:\video goc\<video_goc>\`.
- **BẮT BUỘC** là số nguyên và khớp chính xác công thức:
  $$\text{video gốc} = (\text{slot} - 1) \times 80 + m$$
- Trong cùng 1 file `Tik{slot}.xlsx` (tương ứng 1 ca upload), không 2 máy nào được dùng chung thư mục video gốc để tránh đụng độ và đăng trùng video trong cùng thời điểm.

### 5. Rule 5: `taikhoan_run_safe.xlsx` Invariants
- Mỗi máy có tối đa 8 dòng vật lý.
- Serial phần cứng thiết bị (Cột `Device ID` / Cột 2) **tuyệt đối không được rỗng**.
- Tài khoản TikTok không được trùng lặp giữa các máy khác nhau.

## Cách chạy kiểm tra tự động
```bash
# Chạy kiểm tra toàn bộ 5 rules (mặc định thư mục D:/OneDrive/TaadaaData/kibe):
python "D:/Taadaa/tools/excel_preflight_validator.py"

# Chạy với chế độ dừng ngay khi gặp lỗi FAIL đầu tiên:
python "D:/Taadaa/tools/excel_preflight_validator.py" --exit-on-error

# Chỉ định thư mục khác:
python "D:/Taadaa/tools/excel_preflight_validator.py" --excel-dir "path/to/workbooks"
```
Mã trả về:
- `0`: PASS 100% (an toàn dispatch batch).
- `1`: FAILED (phát hiện vi phạm, log chi tiết file, dòng, cột, máy).

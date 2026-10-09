# Admin Master Folder Video Reconciliation & Cross-Host Safe Sync Playbook

## 1. Bối cảnh & Hiện trạng dữ liệu cụm Admin (Máy 201..280)
- **Cụm Admin**: Gồm 80 máy (STT 201..280).
- **Master Workbook (`admin/taikhoan_dat_v2_updated .xlsx`)**:
  - Sheet `Tài Khoản`: Hiện có 364 tài khoản (365 hàng bao gồm header).
  - Cột B (`Folder Video`): Thường gặp lỗi bị dán nhầm toàn bộ thành `1` hoặc mang giá trị vượt dải >1000 do áp dụng nhầm công thức của Kibe `(m - 1) * 8 + slot` thay vì công thức Admin.
- **8 file Tik con (`Tik1.xlsx` .. `Tik8.xlsx`)**:
  - `Tik1`: 80 accounts
  - `Tik2`: 60 accounts
  - `tik3`: 65 accounts
  - `Tik4`: 11 accounts
  - `Tik5`: 13 accounts
  - `Tik6`: 2 accounts
  - `Tik7`: 56 accounts
  - `Tik8`: 77 accounts
  - **Tổng cộng**: Đúng 364 tài khoản hợp lệ, khớp chính xác 100% (364/364) với các tài khoản trong Master DAT. Cột D (`Folder Video`) trong các file Tik con này đã được tính chuẩn theo công thức `(STT - 201) * 8 + slot` (dải 1..640).

## 2. Quy trình Chuẩn hóa Folder Video từ Tik1..Tik8 sang Master
1. **Bước 1: Trích xuất bản đồ ánh xạ chuẩn từ Tik1..Tik8**:
   - Duyệt qua 8 file `Tik1.xlsx` đến `Tik8.xlsx` tại thư mục `D:\OneDrive\TaadaaData\admin\`.
   - Thu thập key `(stt: int, username: str.strip().lower()) -> folder_video: int`.
2. **Bước 2: Cập nhật Master `taikhoan_dat_v2_updated .xlsx`**:
   - Sao lưu backup an toàn dạng `.bak_standardize_<timestamp>.xlsx`.
   - Mở `taikhoan_dat_v2_updated .xlsx`, sheet `Tài Khoản`.
   - Với mỗi hàng tài khoản: tra cứu `(stt, username)` trong dictionary vừa xây dựng.
   - Gán lại giá trị chuẩn vào Cột 2 (`Folder Video`).
   - Lưu nguyên tử qua file `.tmp` và `os.replace`.

## 3. Quy trình Cập nhật `admin/taikhoan_run_safe.xlsx`
- File `admin/taikhoan_run_safe.xlsx` phục vụ feed/follow của cụm Admin.
- Cấu trúc chuẩn 4 cột: `['May', 'Device ID', 'ID', 'Video Đã Đăng']`.
- Trích xuất 364 tài khoản hợp lệ từ Master (kèm `Video Đã Đăng` lấy từ file Tik tương ứng hoặc fallback `0`).
- Lưu nguyên tử để đảm bảo không bị lock hoặc corrupt bởi tiến trình chạy ngầm.

## 4. Kích hoạt Đồng bộ Danh bạ Gộp Toàn Farm (`sync_combined_safe_workbook.py`)
- Script chuẩn hóa: `D:\Taadaa\tools\sync_combined_safe_workbook.py`.
- Tự động đọc:
  + Kibe: `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` (Máy 1..80)
  + Admin: `D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx` (Máy 201..280)
- Hợp nhất và loại trùng theo `uid_clean` (case-insensitive), xuất ra file `D:\OneDrive\TaadaaData\taikhoan_run_safe_combined.xlsx`.

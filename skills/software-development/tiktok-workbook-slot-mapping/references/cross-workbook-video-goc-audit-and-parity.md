# Quy Trình Kiểm Tra & Chuẩn Hóa Ánh Xạ Video Gốc Tránh Trùng Kênh & Trùng Nguồn (Cross-Workbook Audit)

## 1. Bối cảnh & Phát hiện
Khi người lập bảng gõ nhầm hoặc kéo chuột autofill trong các workbook con `Tik1..Tik8.xlsx`, có thể xảy ra:
- **Trùng số `video gốc`**: 2 máy khác nhau trong cùng 1 Tik (hoặc khác Tik) bị trỏ chung vào 1 thư mục video nguồn trong `D:\video goc`.
  - Ví dụ phát hiện trong `Tik3.xlsx`:
    + M64 (`toansuong04`) và M65 (`hunh.m.linh571`): đều trỏ vào `video gốc = 225`.
    + M66 (`hollyfjzk77`) và M70 (`terrarau61`): đều trỏ vào `video gốc = 226`.
    + M67 (`yaelmssp62p`) và M71 (`anthirifcv8`): đều trỏ vào `video gốc = 227`.
    + M68 (`mautuoi08`) và M72 (`hennitjy34q`): đều trỏ vào `video gốc = 228`.
    + M69 (`lephong3862`) và M73 (`candiswn00k`): đều trỏ vào `video gốc = 229`.
- **Hệ quả**: Khi render, cả 2 máy bốc chung 1 kho clip gốc -> tài khoản đăng clip có nội dung và avatar giống nhau.

## 2. Công thức chuẩn toán học cho Video Gốc toàn Farm
Mỗi máy $m$ ($1 <= m <= 80$) tại slot $k$ ($1 <= k <= 8$) BẮT BUỘC tuân thủ:
- **`Folder Video` (thư mục render trong `D:\TIKTOK-videonuoinick`):**
  Folder Video = (m - 1) * 8 + k
- **`Video Gốc` (thư mục nguồn trong `D:\video goc`):**
  Video Gốc = (k - 1) * 80 + m
  - Tik1: 1 .. 80 (m)
  - Tik2: 81 .. 160 (80 + m)
  - Tik3: 161 .. 240 (160 + m)
  - Tik4: 241 .. 320 (240 + m)
  - Tik5: 321 .. 400 (320 + m)
  - Tik6: 401 .. 480 (400 + m)
  - Tik7: 481 .. 560 (480 + m)
  - Tik8: 561 .. 640 (560 + m)

## 3. Quy trình Audit & Tự động Sửa lệch Mapping
1. Chạy script audit toàn bộ 8 workbook:
   ```python
   import openpyxl
   for k in range(1, 9):
       wb = openpyxl.load_workbook(f'D:/OneDrive/TaadaaData/kibe/Tik{k}.xlsx', read_only=True)
       ws = wb['TaiKhoan']
       for r in list(ws.iter_rows(values_only=True))[1:]:
           m = r[0]
           expected_goc = (k - 1) * 80 + m
           expected_folder = (m - 1) * 8 + k
           if r[4] != expected_goc:
               print(f"LỆCH VIDEO GỐC: Tik{k} M{m} có {r[4]} != {expected_goc}")
   ```
2. Nếu phát hiện lệch, thực hiện sửa cell trực tiếp trên workbook theo đúng công thức.
3. Khi 2 máy đã lỡ render chung video gốc, kiểm tra số video đã đăng:
   - Nếu nick chưa đăng video: Xóa folder render bị trùng và render lại theo video gốc chuẩn mới.
   - Nếu nick đã đăng >= 1 video: Đánh giá xem có cần reseed (đổi kho mới) hay cho đăng nốt các video còn lại rồi chuyển nguồn.

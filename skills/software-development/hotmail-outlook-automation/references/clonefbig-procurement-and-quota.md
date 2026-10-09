# Hotmail OAuth2 Procurement & Farm Quota Calculation

## 1. Nhà Cung Cấp Hotmail OAuth2 (`buy_hotmail.py`)
- **CloneFBIG (Primary)**:
  - Base URL: `https://clonefbig.com`
  - Product ID: `3470` (*Hotmail - Outlook Trusted · Graph API Format · Live 6–12 Months*)
  - Giá: 270đ / acc. Tồn kho thường trực > 5.000 acc.
  - Số dư tài khoản API: `tada`.
  - Luôn mua lẻ từng acc (`amount=1`) qua vòng lặp, kiểm tra Graph token qua endpoint Microsoft OAuth2 (`https://login.microsoftonline.com/consumers/oauth2/v2.0/token`), xác nhận HTTP 200 `access_token` hợp lệ 100% trước khi lưu.
- **BoxTaiKhoan (Fallback)**:
  - Thường xuyên cạn số dư (chỉ còn ~47đ) hoặc lỗi fulfillment phía nhà bán (Product 129). Chỉ dùng khi CloneFBIG hết hàng.

## 2. Lệnh Mua & Nạp Tự Động Theo Dải Máy
- **Cụm Kibe (Máy 1..80)**:
  ```bash
  D:\Taadaa\python-envs\automation\Scripts\python.exe D:\Taadaa\tools\buy_hotmail.py --provider clonefbig --append-kibe <N> [--target-machines M1,M2...]
  ```
  Target file: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
- **Cụm Admin (Máy 201..280)**:
  ```bash
  D:\Taadaa\python-envs\automation\Scripts\python.exe D:\Taadaa\tools\buy_hotmail.py --provider clonefbig --append-admin <N>
  ```
  Target file: `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx`.
  Cơ chế phân bổ: Tự động gán xoay vòng vào máy có số lượng mail ít nhất (tham lam min count) để cân bằng dải 201..280.

## 3. Công Thức Đối Soát Quota Mail Toàn Farm (160 Máy x 8 Slot = 1.280 Acc)
Để chuẩn bị đủ mail cho toàn bộ 160 máy đạt 8 slot/máy:
Cho từng máy $m$:
$$\text{to\_buy}(m) = \max(0, 8 - (\text{active\_tiktok}(m) + \text{clean\_available\_mail}(m)))$$

- **active_tiktok(m)**: Số lượng tài khoản TikTok đã đăng ký thành công (có trong `taikhoan_run_safe.xlsx` hoặc `taikhoan_dat_v2_updated .xlsx`).
- **clean_available_mail(m)**: Số lượng Hotmail sạch trong `gmail_clean_v2.xlsx` của máy $m$ (không nằm trong tracking, trạng thái không chứa `die`, `used`, `khoa`, `banned`).
- **to_buy(m)**: Số lượng mail cần mua nạp thêm.

## 4. Nguyên Tắc Atomic Save Cho File Excel (Chống Corrupt ZIP)
Khi lưu các workbook quan trọng (`taikhoan_dat_v2_updated .xlsx`, `gmail_clean_v2.xlsx`, `taikhoan_run_safe.xlsx`):
- **CẤM TUYỆT ĐỐI**: Lưu trực tiếp `wb.save(path)` trong các tiến trình batch dài hơi hoặc qua mạng OneDrive vì dễ làm hỏng cấu trúc zip (`KeyError: 'xl/workbook.xml'`).
- **BẮT BUỘC**:
  ```python
  tmp_p = path.with_suffix(".tmp.xlsx")
  wb.save(tmp_p)
  tmp_p.replace(path)
  ```

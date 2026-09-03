# Đối soát & Detection Mail Chưa Reg TikTok

## 1. Cơ chế đối soát
- Nguồn mail cấp: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (Sheet `Gmail Accounts`: cột Máy, Email, Pass...).
- Bảng tracking kết quả: `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (Sheet `Tài Khoản`: cột C là `ID` TikTok, cột F là `GMAIL`).
- Tiêu chí mail chưa reg TikTok:
  1. Mail có trong nguồn `gmail_clean_v2.xlsx` (kèm password) nhưng chưa xuất hiện trong bảng `taikhoan_dat_v2_updated .xlsx` có TikTok ID hợp lệ.
  2. Mail đã được add vào bảng `taikhoan_dat_v2_updated .xlsx` nhưng cột C (`ID`) hoặc D (`PASS`) đang trống (chưa hoàn tất đăng ký).

## 2. Pitfall khi chạy `_detect_clean.py`
- Lỗi `DETECTION_BLOCKED: TARGET_INVENTORY_CONFLICT: machine X`:
  - Nguyên nhân: Trong file `taikhoan_run_safe.xlsx` (Sheet `Accounts`), một số dòng ở cột `device id` bị dính giá trị timestamp dạng string (ví dụ `2026-08-18 18:27:39`) khiến hàm `_is_inventory_date_marker` bỏ sót nếu format không khớp tuple định dạng chuẩn hoặc nhận nhầm là serial khác biệt.
  - Xử lý đối soát nhanh: Dùng script Python trực tiếp đối chiếu `gmail_clean_v2.xlsx` vs `taikhoan_dat_v2_updated .xlsx` theo `email.casefold()` để lọc ra danh sách mail chưa reg chính xác mà không bị chặn bởi inventory serial map.

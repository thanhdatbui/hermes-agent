# Quy tắc Xử lý 2FA & Đồng bộ Kho Dữ liệu OneDrive (2026-09-28)

## 1. Ưu Tiên 2FA Authenticator Trước OTP Email
- Khi màn hình TikTok hiển thị "Xác minh 2 bước" với phương thức mặc định là gửi mã về Email (`Sử dụng liên kết này hoặc nhập mã được gửi đến...`):
  - **BẮT BUỘC**: Bấm vào `Sử dụng phương thức khác >` (`[408, 1098]`).
  - Chọn `Trình xác thực` / `Ứng dụng xác thực` (`[540, 1660]`).
  - Dùng mã TOTP sinh từ secret trong database để vượt qua checkpoint.
  - **Chỉ fallback sang OTP Email** khi tài khoản không có 2FA secret hoặc màn hình không hỗ trợ đổi phương thức.
- **Bypass Màn hình Tiểu sử (Bio screen)**:
  - Sau login, nếu TikTok hiện màn hình Tiểu sử ("Bạn có thể chỉnh sửa tiểu sử bất cứ lúc nào..."), bấm `Hủy` / `Bỏ qua` (tọa độ `[95, 138]`).

## 2. Quy Chuẩn Lưu Trữ Kho Backup OneDrive
- Thư mục gốc dữ liệu OneDrive (`D:/OneDrive/TaadaaData/kibe/`) CHỈ ĐƯỢC PHÉP giữ lại các file canonical đang hoạt động:
  - `taikhoan_dat_v2_updated .xlsx`
  - `taikhoan_run_safe.xlsx`
  - `Tik1.xlsx` đến `Tik8.xlsx`
  - `PROXYgandienthoai.xlsx`
  - `master_gmail_manager.xlsx` & `gmail_clean_v2.xlsx`
- Toàn bộ file sao lưu (`.bak`, `.backup_*`, `tx_snap_*`) BẮT BUỘC phải chuyển vào thư mục con tập trung:
  `D:/OneDrive/TaadaaData/kibe/workbook-backups/archive_history/`

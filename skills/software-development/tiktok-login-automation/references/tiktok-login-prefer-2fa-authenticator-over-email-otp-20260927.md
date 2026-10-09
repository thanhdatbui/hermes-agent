# Ưu tiên 2FA Authenticator trước OTP Email & Xử lý Giao diện Mới (2026-09-27)

## 1. Nguyên tắc cốt lõi: Luôn ưu tiên 2FA Authenticator trước OTP Email
- **Hiện tượng**: Trên màn hình "Xác minh 2 bước" (2-step verification) của TikTok, app thường tự động hiển thị luồng gửi mã xác thực về Email (`Sử dụng liên kết này hoặc nhập mã được gửi đến a***6@gmail.com`).
- **Bẫy classifier**: Nếu script chỉ check từ khóa chung chung như `"xac minh 2 buoc"` hoặc điền mã ngay, mã TOTP 6 số sinh từ Authenticator secret sẽ bị điền nhầm vào ô mã OTP Email -> TikTok báo mã sai / hết hạn sau 3 lần thử.
- **Quy trình xử lý chuẩn**:
  1. Khi gặp màn hình 2FA nhưng nội dung là gửi mã về email:
     - Tự động tap vào nút **`Sử dụng phương thức khác >`** (`Su dung phuong thuc khac` / `Use another method`, thường ở tọa độ Center `[408, 1098]`).
  2. Bảng chọn phương thức hiện lên:
     - BẮT BUỘC match cả nhãn **`Trình xác thực`** và **`Ứng dụng xác thực`** / `Authenticator App`. (Trên TikTok Android tiếng Việt, nhãn thực tế là `Trình xác thực`).
  3. Sau khi chuyển sang màn hình Trình xác thực:
     - Điền mã TOTP 6 số từ secret 2FA lưu trong database / tracking.
  4. Chỉ fallback sang đọc mã Email OTP khi:
     - Tài khoản hoàn toàn không có 2FA secret trong tracking, HOẶC
     - Màn hình không có nút đổi phương thức sang Trình xác thực.

## 2. Xử lý màn hình Onboarding Tiểu sử (Bio screen) sau Login
- Sau khi xác thực 2FA thành công, TikTok có thể không vào thẳng feed/profile mà dừng ở màn hình:
  - Text: `"Tiểu sử"`, `"Bạn có thể chỉnh sửa tiểu sử bất cứ lúc nào."`
  - Nút: `"Hủy"` (bounds `[24,72][167,204]`, coord `(95, 138)`) và `"Lưu"`.
- **Cách dismiss**: Trong `handle_post_auth_screens()`, kiểm tra `"tieu su"` / `"chinh sua tieu su"`, bấm `Hủy` hoặc coord fallback `(95, 138)` để vào thẳng Profile / Feed.

## 3. Quy chuẩn kho Backup OneDrive
- Toàn bộ các file `.bak`, `.backup_before_*`, `tx_snap_*` phải được gom dọn tập trung vào:
  `D:/OneDrive/TaadaaData/kibe/workbook-backups/archive_history/`
- Thư mục gốc `D:/OneDrive/TaadaaData/kibe/` chỉ giữ lại các file canonical đang hoạt động (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `Tik1.xlsx`-`Tik8.xlsx`, `PROXYgandienthoai.xlsx`).

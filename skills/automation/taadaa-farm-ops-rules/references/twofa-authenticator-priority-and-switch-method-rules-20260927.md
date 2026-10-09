# Taadaa Farm Rules: Ưu tiên 2FA Authenticator & Fallback OTP Email (2026-09-27)

## Bối cảnh & Nguyên tắc Bất biến
- Khẩu lệnh User: *"thì chọn sử dụng phương thức khác r dùng 2fa đi, luôn ưu tiên 2fa trước otp mail sau"* & *"Cập nhật script luôn đi 2fa ưu tiên r ms fallback sang otp"*.
- **Quy tắc**: Mọi luồng login hoặc verify tài khoản có 2FA trên Farm, script phải ưu tiên tuyệt đối phương thức Authenticator App (TOTP secret) trước. Chỉ fallback sang đọc OTP từ Email (Gmail/Hotmail) khi tài khoản không có 2FA secret hoặc màn hình không có tùy chọn Authenticator.

## Kỹ thuật Thực thi trên UI TikTok
1. **Chuyển đổi phương thức tại màn hình Xác minh 2 bước**:
   - Khi TikTok hiện màn hình 2FA dạng Email OTP, bấm vào nút: `Sử dụng phương thức khác >` (`[408, 1039]` hoặc `[408, 1098]`).
   - Tại popup `Chọn phương thức xác minh`, bấm chọn: `Trình xác thực` / `Ứng dụng xác thực` (`Authenticator app` / `(540, 1662)`).
   - Nạp mã TOTP từ secret base32 lưu trong Excel `taikhoan_dat_v2_updated .xlsx`.
2. **Dismiss Onboarding Tiểu sử (Bio screen)**:
   - Sau khi login, TikTok xuất hiện popup `Tiểu sử` ("Bạn có thể chỉnh sửa tiểu sử bất cứ lúc nào").
   - Bắt buộc tap `Hủy` / `Bỏ qua` (tọa độ `(95, 138)` hoặc bounds `[24,72][167,204]`) để vào thẳng Profile/Feed, tránh timeout luồng login.

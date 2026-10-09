# TikTok Login: Ưu tiên 2FA Authenticator trước OTP Email & Switcher Phương thức (2026-09-28)

## Bối cảnh và Sự cố Thực tế
- Khi đăng nhập tài khoản TikTok đã bật 2FA (có secret Base32 lưu trong database / Excel), TikTok thường mặc định hiển thị màn hình:
  ```text
  Xác minh 2 bước
  Email: Sử dụng liên kết này hoặc nhập mã được gửi đến a***6@gmail.com
  Gửi lại mã
  Sử dụng phương thức khác >
  Tiếp tục
  ```
- **Bẫy phân loại (Classifier Trap)**:
  - Cụm từ `Xác minh 2 bước` xuất hiện cả trên màn hình 2FA Authenticator và màn hình 2FA Email OTP.
  - Nếu script nhận diện `Xác minh 2 bước` là Authenticator App và tự động gõ mã TOTP 6 số vào ô email OTP, TikTok sẽ từ chối 3 lần liên tiếp: *"Mã xác minh email đã hết hạn / không hợp lệ"*.
  - Người vận hành dễ lầm tưởng tài khoản bị sai hoặc mất 2FA.

## Nguyên tắc Vận hành Bắt buộc từ User
1. **Luôn ưu tiên 2FA Authenticator trước, OTP Email sau**:
   - Khi tài khoản có secret 2FA trong kho, tuyệt đối không chấp nhận luồng OTP Email mặc định nếu còn phương thức Authenticator.
2. **Cơ chế Switcher Phương thức Tự động**:
   - Khi gặp màn hình 2FA hiển thị nhận mã qua Email:
     1. Tự động tap vào liên kết **`Sử dụng phương thức khác >`** (`Su dung phuong thuc khac`, `Use another method`, hoặc center coord `[408, 1098]`).
     2. Đợi danh sách phương thức mở ra (bottom sheet).
     3. Nhận diện và chọn: **`Trình xác thực`**, **`Ứng dụng xác thực`**, hoặc **`Authenticator App`** (Center coord `[540, 1660]`).
     4. Sau khi vào đúng form nhập mã TOTP của Trình xác thực, sinh mã từ secret 2FA điền vào và xác nhận.
3. **Màn hình Onboarding Tiểu sử (Bio Screen)**:
   - Sau khi login thành công, TikTok thường xuất hiện màn hình `Tiểu sử` (`Bạn có thể chỉnh sửa tiểu sử bất cứ lúc nào`).
   - Cần nhận diện và bấm `Hủy` / `Bỏ qua` (tọa độ `[95, 138]`) để hoàn tất vào Profile thay vì bị timeout vòng lặp post-auth.

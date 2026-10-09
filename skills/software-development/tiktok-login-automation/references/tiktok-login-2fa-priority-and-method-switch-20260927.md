# TikTok Login 2FA Priority & Method Switch (2026-09-27)

## Bối cảnh & Hiện tượng
Khi đăng nhập TikTok trên thiết bị farm (ví dụ Máy 40, nick `amandabschmi86`), sau bước nhập ID & Mật khẩu đúng, TikTok hiển thị màn hình:
```text
Xác minh 2 bước
Email
Sử dụng liên kết này hoặc nhập mã được gửi đến a***6@gmail.com
Gửi lại mã
Sử dụng phương thức khác >
Tiếp tục
```

## Các Cạm bẫy Nghiêm trọng (Pitfalls)
1. **Cạm bẫy nhầm lẫn 2FA Authenticator vs 2FA Email OTP**:
   - Nếu bộ nhận diện chỉ kiểm tra cụm từ `"xac minh 2 buoc"` hoặc `"2-step verification"`, script sẽ ngộ nhận đây là 2FA Authenticator App và tự ý điền mã TOTP 6 số vào ô mã Email.
   - Kết quả: TikTok từ chối liên tiếp 3 lần (*"Mã xác minh email đã hết hạn / không hợp lệ"*), gây hiểu lầm là secret 2FA bị sai hoặc nick bị lỗi.

2. **Chỉ đạo Người dùng: LUÔN ƯU TIÊN 2FA AUTHENTICATOR TRƯỚC OTP EMAIL**:
   - Khi tài khoản đã lưu khóa 2FA secret (Base32) trong Excel/Database, không được vội vàng đọc OTP Email.
   - BẮT BUỘC bấm vào **`Sử dụng phương thức khác >`** (`Su dung phuong thuc khac` / `Use another method`).

3. **Cạm bẫy nhãn nút lựa chọn của TikTok**:
   - Menu phương thức khác của TikTok trên Android không phải lúc nào cũng là *"Ứng dụng xác thực"* (`Authenticator App`).
   - Trên phiên bản mới/Tiếng Việt, TikTok hiển thị nhãn là: **`Trình xác thực`** (`Trinh xac thuc`).
   - Nếu script thiếu từ khóa `"Trình xác thực"`, việc tìm nút sẽ thất bại và rơi vào bế tắc.

4. **Vượt màn hình Tiểu sử (Bio screen) sau khi Auth thành công**:
   - Sau khi vượt 2FA, TikTok hiển thị onboarding *"Tiểu sử: Bạn có thể chỉnh sửa tiểu sử bất cứ lúc nào... [Hủy] [Lưu]"*.
   - Script cần tự động phát hiện cụm từ `"tieu su"` / `"chinh sua tieu su"` để bấm nút **`Hủy`** (hoặc `Bỏ qua`, tọa độ fallback `[95, 138]`), tránh bị timeout 600s ở bước post-auth.

## Quy trình Chuẩn hóa
1. Kiểm tra màn hình 2FA:
   - Nếu có `"ung dung xac thuc"` / `"authenticator app"` / `"trinh xac thuc"`: Điền TOTP secret.
   - Nếu là màn hình 2FA dạng Email OTP và tài khoản có secret 2FA trong tracking:
     - Tap **`Sử dụng phương thức khác`**.
     - Chờ 1.5s, tap **`Trình xác thực`** / **`Ứng dụng xác thực`**.
     - Chờ 1.5s, lấy mã TOTP sinh theo epoch thiết bị điền vào form.
     - Tick *"Tin tưởng thiết bị này"*.
     - Tap *"Tiếp tục"*.
   - Nếu tài khoản KHÔNG có secret 2FA hoặc menu không có Trình xác thực: Mới fallback sang mở hòm thư Gmail/Outlook lấy mã OTP.

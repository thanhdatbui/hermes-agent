# TikTok 2FA Authenticator Priority & GPM OTP Integration (2026-09-28)

## 1. Ưu Tiên 2FA Authenticator Trước OTP Email
- **Bối cảnh**: TikTok thường mặc định hiển thị màn hình 2FA với lựa chọn gửi mã OTP về Email ("Sử dụng liên kết này hoặc nhập mã được gửi đến...").
- **Quy tắc bất di bất dịch**:
  - KHÔNG nhập mã TOTP vào ô Email OTP (gây lỗi "Mã xác minh email đã hết hạn/không hợp lệ").
  - Phải bấm vào `Sử dụng phương thức khác >` (tọa độ `[408, 1098]` hoặc tìm text "Su dung phuong thuc khac" / "Use another method").
  - Chọn `Trình xác thực` / `Ứng dụng xác thực` (`Authenticator app`).
  - Lấy mã TOTP sinh từ cột secret 2FA trong tracking Excel để điền vào.
  - Chỉ fallback sang Email OTP khi tài khoản hoàn toàn không có secret 2FA Authenticator hoặc màn hình không cho đổi phương thức.

## 2. Tự Động Bỏ Qua Màn Hình Tiểu Sử (Bio Screen)
- Sau khi đăng nhập, TikTok thường hiện màn hình onboarding: *"Tiểu sử: Bạn có thể chỉnh sửa tiểu sử bất cứ lúc nào... [Hủy] [Lưu]"*.
- Trong `handle_post_auth_screens()`, tự động tap nút `Hủy` / `Bỏ qua` (tọa độ `[95, 138]`) để vượt qua vào thẳng Profile/Feed.

## 3. Chống Spam Mật Khẩu Sai (Password Lockout Guard)
- Nếu đã điền mật khẩu 1 lần mà màn hình vẫn ở form nhập password (hoặc xuất hiện thông báo "Sai tài khoản hoặc mật khẩu"), CẤM TUYỆT ĐỐI điền lại lần 2 để tránh bị TikTok khóa tài khoản ("Còn X lần thử").
- Dừng ngay (`AUTH_BLOCKED`), chụp ảnh hiện trường và chuyển sang phương thức OTP email hoặc báo cáo User.

## 4. Cơ Chế Lấy OTP Hotmail Qua GPM-Login (Playwright CDP)
- Script: `D:/Taadaa/Hotmail/scripts/read_otp_gpm.py`
- Export: `hotmail_provider.read_tiktok_otp_from_gpm_profile(profile_id_or_email, timeout=120)`
- Quy trình:
  1. Tìm Profile GPM theo email (gán đúng proxy theo mapping máy S7).
  2. Start profile, kết nối Playwright CDP qua `remote_debugging_address`.
  3. Mở `https://outlook.live.com/mail/0/`, xử lý banner cookie.
  4. Quét thư từ `TikTok`, bóc tách mã OTP 6 số.
  5. Đóng context và gọi `stop_profile()` trong khối `finally` để giải phóng RAM.

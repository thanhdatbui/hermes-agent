# Triage & Pitfall: Phân biệt 2FA Authenticator App vs 2FA Email OTP (2026-09-27)

## Bối cảnh & Hiện tượng
Khi đăng nhập tài khoản TikTok đã kích hoạt bảo vệ 2 bước (2FA) nhưng chưa thiết lập Authenticator App (hoặc TikTok yêu cầu xác minh qua email), app sẽ hiển thị màn hình:
```text
Xác minh 2 bước
Email
Sử dụng liên kết này hoặc nhập mã được gửi đến a***6@gmail.com
[Gửi lại mã]
Sử dụng phương thức khác >
[Tiếp tục]
```
Màn hình này yêu cầu mã 6 số gửi về **hộp thư Email (Gmail/Hotmail/Outlook)**.

## Cạm bẫy chí tử (The 2FA Classifier Trap)
1. Trong nhiều script login cũ, bộ nhận diện 2FA định nghĩa:
   ```python
   TWOFA_HINTS = ["ung dung xac thuc", "authenticator app", "xac minh 2 buoc", "2-step verification"]
   ```
2. Cụm từ `"xac minh 2 buoc"` hoặc `"2-step verification"` xuất hiện trên **CẢ HAI** loại màn hình (cả Authenticator App lẫn Email OTP).
3. Do kiểm tra `TWOFA_HINTS` chung chung, script nhận định nhầm màn hình Email OTP là Authenticator App, dẫn tới:
   - Script gọi `pyotp.TOTP(secret).now()` để sinh mã 6 số từ chuỗi secret 2FA trong tracking.
   - Nhập mã TOTP này vào ô mã Email OTP của TikTok.
   - TikTok từ chối mã (vì mã sinh ra từ TOTP không khớp với mã ngẫu nhiên vừa gửi về hòm thư).
   - Lặp lại 3 lần làm tài khoản bị block tạm thời với lỗi `Ma 2FA khong qua sau 3 lan`, gây hiểu nhầm nghiêm trọng là *"Tài khoản bị mất secret hoặc bị đổi 2FA"*.

## Giải pháp chuẩn hóa
1. **Tách biệt rõ ràng 2 loại màn hình 2FA**:
   - `AUTHENTICATOR_APP_HINTS`: Chỉ kích hoạt khi có từ khóa đặc thù của ứng dụng xác thực: `"ung dung xac thuc"`, `"authenticator app"`, `"google authenticator"`.
   - `EMAIL_2FA_HINTS`: Khi màn hình có `"xac minh 2 buoc"` nhưng đi kèm `"email"`, `"gui den"`, hoặc hiển thị địa chỉ mail masked (`a***@...`).
2. **Quy trình xử lý**:
   - Nếu là **Authenticator App 2FA**: Đọc secret Base32 từ file tracking, tính TOTP theo timestamp và nhập.
   - Nếu là **Email 2FA**: Chuyển ngay sang `handle_tiktok_email_otp()` để lấy mã từ Gmail qua IMAP/app hoặc Hotmail qua Graph API/Outlook. Tuyệt đối không nhập TOTP vào ô mã Email.

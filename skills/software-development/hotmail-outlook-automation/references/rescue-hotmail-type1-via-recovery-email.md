# Cứu Hộ Hotmail Loại 1 (Không Có OAuth Token) Qua Email Khôi Phục (2026-09-23)

## 1. Bản chất sự cố
- Hotmail loại 1 (chỉ có `email|password`, không có chuỗi OAuth refresh token `M.C522...` hay client ID): Microsoft đã chặn 100% Basic Auth qua IMAP/POP3.
- Khi đăng nhập vào ứng dụng Outlook trên điện thoại hoặc trình duyệt, Microsoft thường báo "Mật khẩu không đúng" hoặc yêu cầu xác minh bảo mật qua email khôi phục (dạng `th*****@gmail.com`).

## 2. Quy trình giải cứu tự động chuẩn (Đã nghiệm thu trên Máy 32)
1. **Gửi mã OTP về email khôi phục**:
   - Tại màn hình xác minh email của Microsoft, nhập địa chỉ email khôi phục chuẩn của farm: `thanhdatbui1995@gmail.com` vào ô `proof-confirmation-email-input`.
   - Bấm nút `Gửi mã` (resource-id hoặc text 'Gửi mã').
2. **Đọc OTP tự động qua IMAP**:
   - Sử dụng credentials có sẵn trong biến môi trường:
     + `OTP_MAIL_USER`: `thanhdatbui1995@gmail.com`
     + `OTP_MAIL_APP_PASSWORD`: App password Google
   - Gọi hàm `fetch_latest_otp(host='imap.gmail.com', user=..., password=..., not_before_ts=time.time()-120)`.
   - Nhận mã 6 chữ số từ email có Subject `Your single-use code`.
3. **Điền mã vào app Outlook**:
   - Màn hình nhập mã gồm 6 ô riêng biệt (`codeEntry-0` đến `codeEntry-5`).
   - Gõ từng chữ số vào từng ô tương ứng qua ATX tap hoặc `adb shell input text`.
   - Bấm `OK` / `Tiếp theo`.
4. **Vượt Onboarding Outlook App**:
   - Vượt qua màn hình "Ghi chú nhanh về tài khoản Microsoft": Bấm `OK` (2 lần).
   - "Thêm một tài khoản khác": Bấm `CÓ LẼ ĐỂ SAU` (tọa độ bottom nav start).
   - "Dữ liệu của bạn": Bấm `TIẾP THEO` -> `CHẤP NHẬN` -> `TIẾP TỤC VỚI OUTLOOK`.
   - Hòm thư mở ra thành công với đầy đủ các email xác minh.

## 3. TikTok Login Fast-Path với 2FA TOTP
- Khi hòm thư đã mở trên Outlook app, TikTok có thể gửi mã xác minh email hoặc yêu cầu 2FA.
- **Mẹo tối ưu**: Nếu tài khoản TikTok có khóa bí mật 2FA TOTP trong cơ sở dữ liệu (`account_row['twofa']`):
  + Tại màn hình TikTok đòi mã email, bấm `Sử dụng phương thức khác >`.
  + Chọn `Trình xác thực` (Authenticator).
  + Dùng thư viện `pyotp.TOTP(secret).now()` sinh mã 6 số tức thì và điền vào ô mã.
  + Bấm `Tiếp tục` (tọa độ `[96,1728][984,1884]`, center `(540, 1806)`).
  + Giúp đăng nhập ngay lập tức mà không phải chờ đợi email hay lo ngại độ trễ mạng!

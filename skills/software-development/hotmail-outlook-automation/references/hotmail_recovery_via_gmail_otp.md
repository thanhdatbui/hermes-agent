# Cứu Hotmail Bị Khóa / Sai Mật Khẩu Qua Email Khôi Phục (Recovery Email)

## 1. Bối cảnh & Nguyên nhân
- Hotmail loại cũ (loại 1) không có Refresh Token OAuth2 (Graph API).
- Khi đăng nhập vào ứng dụng Outlook trên điện thoại hoặc web, Microsoft báo:
  `Mật khẩu đó không đúng với tài khoản Microsoft của bạn`
  hoặc phát hiện thiết bị lạ và chặn đăng nhập, yêu cầu:
  `Xác minh email của bạn: Chúng tôi sẽ gửi mã đến th*****@gmail.com`
- Email khôi phục mặc định toàn farm: `thanhdatbui1995@gmail.com` (đã cấu hình qua IMAP `OTP_MAIL_USER` và `OTP_MAIL_APP_PASSWORD`).

## 2. Quy Trình Cứu Hộ Từng Bước (Recovery Pipeline)
1. **Điền Email Khôi Phục**:
   - Node: `EditText` có resource-id `proof-confirmation-email-input` (center khoảng `(540, 912)`).
   - Nhập chuỗi: `thanhdatbui1995@gmail.com`.
   - Tap nút `Gửi mã` (resource-id Button, center khoảng `(540, 1131)`).
2. **Đọc Mã OTP Từ Gmail Qua IMAP**:
   - Sử dụng hàm `fetch_latest_otp` từ `D:/Taadaa/Hotmail/flows/hotmail_recovery.py`:
     ```python
     from flows.hotmail_recovery import fetch_latest_otp
     u = os.environ.get('OTP_MAIL_USER')
     p = os.environ.get('OTP_MAIL_APP_PASSWORD')
     res = fetch_latest_otp(
         host='imap.gmail.com',
         user=u,
         password=p,
         not_before_ts=time.time() - 300,
         max_messages=10,
     )
     # res[0] là mã OTP 6 số (Subject: 'Your single-use code')
     ```
3. **Điền Mã OTP 6 Số**:
   - Microsoft chia thành 6 ô riêng biệt: `codeEntry-0` đến `codeEntry-5`.
   - Nhập từng ký tự vào từng ô hoặc tap từng ô rồi gõ số tương ứng.
4. **Vượt Qua Các Màn Hình Interstitial (Onboarding) Outlook**:
   - `Ghi chú nhanh về tài khoản Microsoft`: Tap `OK` (center `(828, 1734)`).
   - `Dữ liệu của bạn, theo cách của bạn`: Tap `TIẾP THEO` (center `(886, 1836)`).
   - `Cùng nhau cải thiện`: Tap `CHẤP NHẬN` (center `(886, 1836)`).
   - `Nâng tầm trải nghiệm`: Tap `TIẾP TỤC VỚI OUTLOOK` (center `(800, 1836)`).
   - `Thêm một tài khoản khác`: Tap `CÓ LẼ ĐỂ SAU` (center `(180, 1836)`).
5. **Nghiệm Thu**:
   - Màn hình chuyển vào `Hộp thư đến` của Outlook. Chụp ảnh nghiệm thu xác nhận hòm thư đã active.

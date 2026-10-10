# Hotmail Recovery OTP Flow via GPM & Gmail IMAP

## 1. Context & Signals
- Khi đăng nhập Hotmail trên web/GPM gặp thông báo sai mật khẩu hoặc checkpoint đòi xác minh:
  - Nếu xuất hiện màn hình: *"Xác minh email của bạn - Chúng tôi sẽ gửi mã đến th*****@gmail.com"* -> Đây là bằng chứng 100% tài khoản đã từng được gán mail khôi phục cá nhân (`thanhdatbui1995@gmail.com`).
  - Nếu xuất hiện form: *"Khôi phục tài khoản của bạn - Nhập địa chỉ email khác để liên hệ..."* -> Tài khoản chưa gán mail khôi phục cá nhân, không thể cứu bằng luồng OTP tự động.

## 2. Quy trình cứu nick tự động qua GPM + Playwright + Gmail IMAP
1. **Xác nhận mail khôi phục:**
   - Điền email khôi phục đầy đủ (`thanhdatbui1995@gmail.com`) vào selector `#proof-confirmation-email-input`.
   - Bấm `button:has-text('Gửi mã')`.
2. **Lấy mã OTP từ Gmail qua IMAP:**
   - Đọc credentials từ Windows Environment (`winreg.HKEY_CURRENT_USER\Environment`):
     - `OTP_MAIL_USER`: `thanhdatbui1995@gmail.com`
     - `OTP_MAIL_APP_PASSWORD`: App password (16 ký tự).
   - Kết nối `imap.gmail.com:993`, tìm thư từ `Microsoft` / `account-security-noreply@accountprotection.microsoft.com`.
   - Trích xuất mã 6 chữ số: `re.findall(r"\b(\d{6})\b", body)`.
   - **QUAN TRỌNG:** Bỏ qua mã `521839` (đây là ID link điều khoản bảo mật của Microsoft, không phải OTP).
3. **Điền OTP trên web:**
   - Microsoft dùng 6 ô input riêng biệt: `#codeEntry-0` đến `#codeEntry-5`.
   - Lặp qua từng ký tự và điền vào từng ô tương ứng (delay 0.1s).
4. **Xử lý các màn hình chuyển tiếp sau khi nhập OTP:**
   - **Điều khoản (Terms):** Nút *"Tiếp theo"* (`button:has-text('Tiếp theo'), #iNext`).
   - **Duy trì đăng nhập (KMSI):** Bấm *"Không"* (`#idBtn_Back`, `input[value='Không']`) hoặc *"Có"* (`#idSIButton9`). *Lưu ý: Bấm "Không" giúp chuyển hướng ngay lập tức vào dashboard, tránh bị kẹt màn hình KMSI.*
   - **Cookie Consent:** Bấm *"Chấp nhận"* (`button:has-text('Chấp nhận'), #acceptButton`).
5. **Rate limit & Cooldown:**
   - Nếu gửi OTP quá 3 lần liên tiếp trong thời gian ngắn, Microsoft sẽ báo: *"Bạn đã đạt đến giới hạn của mình với phương thức đăng nhập này"*.
   - Xử lý: Set cooldown tối thiểu 2 giờ trong file state để hạ nhiệt trước khi thử lại.

## 3. Pitfalls & Invariants
- **CẤM fallback sang mật khẩu TikTok:** Khi đăng nhập Hotmail, tuyệt đối không được fallback sang cột `password` (mật khẩu TikTok). Phải lấy đúng cột `PASS MAIL` / `mail_password`.
- **Tránh dùng thuật ngữ rườm rà với User:** Dùng từ ngữ đơn giản, rõ ràng (ví dụ: "tên nick TikTok" thay vì "TikTok ID handle").

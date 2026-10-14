# GPM Google OAuth Password Confirmation, 2FA Handling & Master Workbook SoT

## 1. Bản chất sự cố
Khi tự động hóa OAuth Google (ví dụ cấp quyền cho Antigravity / OmniRoute) trên trình duyệt GPM:
- Google thường hiển thị màn hình xác nhận mật khẩu ("Chào mừng <email> - Nhập mật khẩu của bạn") hoặc thử thách danh tính ("Xác minh danh tính của bạn").
- **Cạm bẫy sai lầm 1 (Ảo tưởng Chrome Autofill):** Profile GPM thường chỉ lưu session cookies hoặc token, không lưu sẵn mật khẩu trong `chrome://password-manager`. Việc click vào ô input rồi gửi phím `Enter` sẽ submit chuỗi rỗng và bị Google chặn lại tại chỗ.
- **Cạm bẫy sai lầm 2 (Hành vi đóng băng / Luna Behavior):** Coordinator thấy ô password thì viện cớ "Safety Rule cấm gõ mật khẩu" để dừng lại hỏi `clarify`. Đây là vi phạm nghiêm trọng: tài khoản thuộc quyền sở hữu của user trên farm/GPM, đã có lệnh tự động hóa login thì phải tra cứu credential để điền dứt điểm, cấm thoái thác hỏi user những điều đã có sẵn dữ liệu.

## 2. Nguồn dữ liệu xác thực (Source of Truth)
- File Excel tổng quản lý Gmail: `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (Sheet `Master_All`).
- Cột cấu trúc:
  - Cột 1: STT
  - Cột 2: Email
  - Cột 3: Password thật
  - Cột 4: Recovery_Email
  - Cột 5: 2FA_Secret (chuỗi base32 TOTP secret, ví dụ `GQTDCJSGYEJRAMPIKIZK2UGVWFDQXXJR`)
  - Cột 7: Trạng thái (LIVE/DIE)

## 3. Quy trình tự động hóa Playwright + TOTP chuẩn xác
1. **Đọc trước credentials từ Excel:**
   Tra cứu `email` trong `master_gmail_manager.xlsx` để lấy `password` và `2fa_secret`.
2. **Xử lý form Password:**
   ```python
   pwd_input = page.locator("input[type='password']")
   if pwd_input.count() > 0 and pwd_input.first.is_visible():
       pwd_input.first.fill(account_password)
       time.sleep(1)
       pwd_next = page.locator("#passwordNext")
       if pwd_next.count() > 0 and pwd_next.first.is_visible():
           pwd_next.first.click()
       else:
           pwd_input.first.press("Enter")
       time.sleep(3)
   ```
3. **Xử lý thử thách 2FA / TOTP:**
   Nếu Google chuyển sang màn hình 2-step verification đòi mã 6 số:
   ```python
   import pyotp
   if account_2fa_secret:
       totp = pyotp.TOTP(account_2fa_secret)
       code = totp.now()
       totp_input = page.locator("input[type='tel'], input#idvPin, input[name='totpPin']")
       if totp_input.count() > 0 and totp_input.first.is_visible():
           totp_input.first.fill(code)
           page.locator("#totpNext, button:has-text('Tiếp theo'), button:has-text('Next')").first.click()
   ```
4. **Cấp quyền OAuth:**
   Khi xuất hiện màn hình consent/allow ("Google Antigravity muốn truy cập..."):
   Click `#submit_approve_access` hoặc nút `button:has-text('Tiếp tục')`, `button:has-text('Cho phép')`.

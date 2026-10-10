# Quy trình Đổi Email Liên Kết TikTok sang Hotmail Sạch (Clean Hotmail) qua 2FA TOTP & Graph API (2026-10-10)

## 1. NGUYÊN LÝ BƯỚC NGOẶT: TIKTOK CHO PHÉP ĐỔI EMAIL KHÔNG CẦN MAIL CŨ KHI CÓ 2FA
- **Hiện tượng**: Nhiều tài khoản TikTok già (aged account, nhiều follow, đã đăng nhiều video) có Gmail gốc bị DIE (Google vô hiệu hóa/khóa tài khoản, ghi nhận trong `gmail_die_tong.txt`).
- **Sai lầm phổ biến**: Đánh đồng "Gmail die = TikTok die", vội vã khai tử nick và thay bằng nick non mới reg, làm lãng phí tài sản farm.
- **Thực tế kỹ thuật**:
  - Khi nick TikTok đã bật **Trình xác thực (Authenticator App / 2FA TOTP)** độc lập (Cột E Master Excel):
  - Khi vào `Hồ sơ` ➔ `Cài đặt và quyền riêng tư` ➔ `Tài khoản` ➔ `Thông tin người dùng / tài khoản` ➔ `Email` ➔ bấm **"Thay đổi email"**:
  - **TikTok KHÔNG đòi OTP từ Gmail cũ đã die**, mà mở màn hình xác minh danh tính bằng **mã 2FA TOTP 6 số** (sinh từ Secret Key Cột E bằng `pyotp`) hoặc **Mật khẩu TikTok**.
  - Vượt qua bước này, TikTok mở thẳng form **"Nhập địa chỉ email mới"**.

---

## 2. TIÊU CHUẨN CHỌN HOTMAIL MỚI LIÊN KẾT (CLEAN HOTMAIL INVARIANTS)
Khi chọn Hotmail để link vào tài khoản TikTok chính thức:
1. **Chưa từng đăng ký / liên kết TikTok**:
   - Kiểm tra hộp thư qua Microsoft Graph API: chỉ chứa các thư thông báo bảo mật mặc định của Microsoft (`Welcome to your new Outlook.com account`, `security activity`), tuyệt đối KHÔNG chứa thư xác minh hay thông báo từ `noreply@account.tiktok.com`.
2. **Có OAuth Refresh Token LIVE 100%**:
   - Kiểm tra đổi token `exchange_refresh_token(rt, cid)` trả về HTTP 200 và `access_token` hợp lệ.
3. **Không xung đột sổ sách**:
   - Email chưa từng xuất hiện trong `taikhoan_dat_v2_updated .xlsx` (Cột 6) và `tiktok_tracker.db`.

---

## 3. QUY TRÌNH TỰ ĐỘNG HÓA A-Z (`change_email_m20.py` / `change_email_m2.py`)
1. **Khóa thiết bị an toàn**:
   - Bắt buộc bọc trong `operator_device_lock(machine=M, serial=SERIAL, project="change_email_m...")` để tôn trọng bulkhead farm.
2. **Điều hướng UI TikTok**:
   - Mở app TikTok, vào Hồ sơ nick đích.
   - Mở Menu 3 gạch ➔ `Cài đặt và quyền riêng tư` (toạ độ an toàn `[621, 1248]` hoặc regex text).
   - Chọn `Tài khoản` (`[540, 350]`) ➔ `Thông tin người dùng / tài khoản` (`[540, 300]`).
   - Tap dòng `Email` ➔ Tap `Thay đổi email`.
3. **Vượt Checkpoint Xác minh**:
   - Nếu màn hình hỏi mã 6 số từ Authenticator: sinh mã `code = pyotp.TOTP(secret).now()`, điền vào qua `adb shell input text <code>`.
   - Nếu hỏi mật khẩu TikTok: điền mật khẩu hiện tại ➔ Bấm Tiếp tục.
4. **Nhập Hotmail mới & Bấm Gửi mã**:
   - Focus ô EditText nhập email ➔ điền `HOTMAIL_EMAIL`.
   - Bấm nút `Gửi mã` / `Tiếp tục` (`[540, 813]`).
5. **Đọc OTP tự động qua Microsoft Graph API (Zero-UI trên Hotmail)**:
   - Polling endpoint `https://graph.microsoft.com/v1.0/me/messages?$top=10&$orderby=receivedDateTime desc` mỗi 3-4 giây (timeout tối đa 75s).
   - Lọc thư từ TikTok, regex bắt mã 6 chữ số: `re.findall(r"\b(\d{6})\b", subject + body)`.
6. **Nhập OTP vào TikTok**:
   - Dùng lệnh `adb shell input keyevent` (map ký tự 0-9 sang keycodes 7-16) để gõ chính xác mã OTP vào TikTok.
   - Chờ TikTok cập nhật màn hình Thông tin người dùng thành `Email: <chữ_cái_đầu>***<chữ_cái_cuối>@hotmail.com >`.
7. **Đồng bộ Master Excel**:
   - Cập nhật ngay lập tức:
     * Cột F (GMAIL/EMAIL): Hotmail mới vừa đổi.
     * Cột G (PASS MAIL): Mật khẩu Hotmail mới.
   - Chụp ảnh nghiệm thu và dùng WinRT OCR soi mắt kiểm chứng trước khi kết thúc ca.

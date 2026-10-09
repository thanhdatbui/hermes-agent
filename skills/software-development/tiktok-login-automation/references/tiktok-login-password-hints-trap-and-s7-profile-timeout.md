# TikTok Login: Bẫy Substring Password vs OTP Hints & Timeout Profile Samsung S7 (2026-09-23)

## 1. Bẫy Substring trong Nhận diện Màn hình: `OTP_HINTS` vs `PASSWORD_HINTS`

### Hiện tượng & Root Cause:
- Trong script `D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py`, hàm `drive_login_screens()` lặp qua các màn hình và kiểm tra từ khóa:
  ```python
  if any(h in flat for h in OTP_HINTS):
      ...
  if any(h in flat for h in PASSWORD_HINTS):
      ...
  ```
- Danh sách `OTP_HINTS` ban đầu chứa chuỗi `"nhap ma"`.
- Khi người dùng hoặc script nhập TikTok ID / Email, TikTok đưa đến màn hình **"Nhập mật khẩu"**.
- Sau khi chuẩn hóa không dấu: `strip_accents("Nhập mật khẩu").lower() == "nhap mat khau"`.
- **BẪY SUBSTRING:** Chuỗi `"nhap ma"` là tiền tố nằm trọn vẹn trong `"nhap mat khau"` (`"nhap ma" + "t khau"`).
- Kết quả: `any(h in flat for h in OTP_HINTS)` trả về `True` ngay lập tức!
- Script nhận diện nhầm màn hình "Nhập mật khẩu" thành màn hình "Xác minh Email / Nhập mã OTP", bỏ qua ô nhập mật khẩu và nhảy vào luồng tìm hộp thư, mở app Outlook trên điện thoại và dừng lại với lỗi `OUTLOOK_APP_INBOX_NOT_VERIFIED`.

### Bản vá bắt buộc (Commit 2026-09-23):
1. **Thêm khoảng trắng bảo vệ trong `OTP_HINTS`**:
   - Đổi `"nhap ma"` thành `"nhap ma "` (có khoảng trắng ở cuối). Tuyệt đối cấm bare `"nhap ma"`.
   - Ưu tiên các markers rõ ràng: `"ma xac nhan"`, `"ma xac minh"`, `"gui lai ma"`, `"verification code"`.
2. **Đảo thứ tự ưu tiên trong `drive_login_screens()`**:
   - Nhánh `PASSWORD_HINTS` (`"mat khau"`, `"password"`, `"enter password"`, `"tao mat khau"`) **BẮT BUỘC ĐỨNG TRƯỚC** nhánh `OTP_HINTS`.
   - Nếu màn hình có ô Password hoặc text "Nhập mật khẩu", script phải ưu tiên điền mật khẩu trước. Chỉ khi màn hình không có password mà yêu cầu OTP thì mới xử lý OTP.

---

## 2. Timeout Load Tab Hồ sơ trên Samsung Galaxy S7 (Android 7)

### Hiện tượng & Root Cause:
- Các máy Samsung Galaxy S7 (`SM-G930F/S/K/L`) cấu hình cũ, sau khi mở app TikTok từ Launcher/Feed, bấm vào tab "Hồ sơ" mất từ 20 đến 30 giây để render hoàn chỉnh giao diện Profile.
- Trong `D:/Taadaa/Tiktok_Reg/social_reg_v1.py`, hàm `_wait_profile_screen_ready(device_id, timeout=12)` và các lần fallback `timeout=6` quá ngắn (chỉ 6 - 12 giây).
- Do chưa load xong, XML dump vẫn ở màn hình Video Feed (`long_press_layout`, `Trang chủ`), hàm `_is_personal_profile_screen_xml()` trả về `False`. Script kết luận không mở được Profile và fail ở bước `[03_dropdown] Khong mo duoc account dropdown`.

### Bản vá bắt buộc:
- Tăng default timeout của `_wait_profile_screen_ready(device_id, timeout=25)`.
- Tăng các lần fallback call từ `timeout=6` lên `timeout=20`.

---

## 3. Quy tắc Phân biệt Hotmail Loại 1 (Không Token) vs Loại 2 (Có OAuth Graph Token)

Khi TikTok bắt buộc gửi OTP về Hotmail/Outlook:
1. **Hotmail Loại 2 (Có Token OAuth2 Graph API):**
   - Đã mua từ boxtaikhoan / lưu trong `gmail_clean_v2.xlsx` cột token `M.C522...` + `client_id`.
   - Script tự động đọc OTP/Magic link từ PC qua HTTP Microsoft Graph API (`https://graph.microsoft.com/v1.0/me/messages`).
   - **CẤM TUYỆT ĐỐI mở app Outlook trên thiết bị Android** khi mailbox đã có token.
2. **Hotmail Loại 1 (Không có Token, chỉ có `mail | password`):**
   - Microsoft đã chặn hoàn toàn Basic Auth (IMAP/SMTP password) cho người dùng Hotmail cá nhân.
   - PC không thể đọc IMAP trực tiếp từ xa.
   - **BẮT BUỘC đăng nhập tài khoản vào app Outlook trên máy Android** bằng kịch bản:
     ```bash
     HOTMAIL_PASSWORD="<pass>" python D:/Taadaa/Hotmail/flows/login_outlook_one_machine.py --machine <N> --serial <SERIAL> --email <EMAIL> --user-authorized
     ```
   - Sau khi hòm thư đã có trong app Outlook trên thiết bị, script `tiktok_login_v1.py` sẽ tự động chuyển sang đọc OTP từ giao diện app Outlook trên máy để hoàn tất đăng nhập TikTok.

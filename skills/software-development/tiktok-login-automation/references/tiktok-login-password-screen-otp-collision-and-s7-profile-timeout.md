# Bẫy Trùng Khớp Substring OTP_HINTS Đè Màn Hình Password & Timeout Profile Screen Ready Trên Samsung S7 (2026-09-23)

## 1. Bối cảnh & Hiện tượng lỗi thực tế
Khi chạy nạp lại tài khoản bằng `tiktok_login_v1.py` trên các máy farm Samsung S7 (SM-G930F/S):
1. **Lỗi 1 (Timeout mở Switcher Dropdown)**:
   - Script gọi `_try_open_account_dropdown_once` nhưng liên tục in:
     `→ profile screen not ready before dropdown, tap profile tab once`
     `→ rv5/sticky chưa thấy, vuốt lên 400px thử lại (1/3)...`
   - Cuối cùng dừng với: `STOPPED: [03_dropdown] Khong mo duoc account dropdown`.
   - **Root Cause**: Hàm `_wait_profile_screen_ready(device_id, timeout=12)` (và retry 6s) có trần timeout quá ngắn. Trên Samsung S7 sau khi phát feed, chuyển sang tab Profile cần từ 20-30s để render hoàn chỉnh.
   - **Khắc phục**: Tăng timeout trong `_wait_profile_screen_ready` từ `12s` lên `25s`, các lệnh gọi fallback từ `6s` lên `20s`.

2. **Lỗi 2 (Bẫy Substring "nhap ma" đè "nhap mat khau")**:
   - Khi TikTok đưa người dùng đến màn hình **"Nhập mật khẩu"** (`bounds=[138,564][852,624]`), script lại log:
     `[7-login] detect_after_continue=registered`
     `[auth] round 1/6`
     `[7c] Lấy OTP TikTok từ inbox: <email>`
     `STOPPED: OUTLOOK_APP_INBOX_NOT_VERIFIED`
   - **Root Cause**:
     - `strip_accents("Nhập mật khẩu").lower()` cho kết quả là `"nhap mat khau"`.
     - Trong danh sách `OTP_HINTS` có chuỗi `"nhap ma"`. Do `"nhap ma"` là tiền tố của `"nhap mat khau"`, điều kiện `any(h in flat for h in OTP_HINTS)` trả về `True` ngay lập tức!
     - Trong `drive_login_screens`, nhánh kiểm tra `OTP_HINTS` lại đặt TRƯỚC `PASSWORD_HINTS`.
     - Hậu quả: Script nhận diện nhầm màn hình nhập Password thành màn hình đòi OTP email, bỏ qua ô nhập mật khẩu và chuyển sang mở app Outlook tìm thư xác minh, dẫn đến thất bại.
   - **Khắc phục**:
     - Đổi `"nhap ma"` thành `"nhap ma "` (có khoảng trắng ở cuối) hoặc `"nhap ma xac"` để không bao giờ match nhầm `"nhap mat khau"`.
     - Đảo nhánh `PASSWORD_HINTS` lên trước `OTP_HINTS` trong `drive_login_screens` (nếu có ô mật khẩu phải ưu tiên điền mật khẩu trước).

3. **Lỗi 3 (Microsoft tắt Basic Auth IMAP cho Hotmail)**:
   - Microsoft đã ngắt hoàn toàn cơ chế đăng nhập IMAP bằng username/password thường đối với Hotmail cá nhân (`AUTHENTICATE failed. Provided authentication mechanism is not supported`).
   - Mọi luồng đọc OTP từ Hotmail loại 2 không có Graph API OAuth2 token bắt buộc phải được đăng nhập sẵn trên app Outlook của thiết bị.

4. **Kỷ luật điều phối khi nhận alert văng / thiếu nick**:
   - Khi nhận cảnh báo `account-switcher-missing-expected`, Coordinator BẮT BUỘC lập tức kích hoạt flow nạp lại chính thức `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <ID_hoặc_email> --ss` thay vì chỉ dừng lại ở bước inspect báo cáo hiện trường.

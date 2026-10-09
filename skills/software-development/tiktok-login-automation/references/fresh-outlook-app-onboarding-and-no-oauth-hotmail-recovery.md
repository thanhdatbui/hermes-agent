# Fresh Outlook App Onboarding & No-OAuth Hotmail Recovery in TikTok Login

## 1. Phân biệt Hotmail Loại 1 vs Loại 2
- **Loại 2 (Mail|Pass|Refresh_Token|Client_ID)**: Mua từ boxtaikhoan có OAuth token. Đọc OTP trực tiếp qua Microsoft Graph API trên PC (`https://graph.microsoft.com/v1.0/me/messages`), hoàn toàn không chạm vào điện thoại.
- **Loại 1 (Mail|Pass thuần túy, không có OAuth Token)**: Các tài khoản tạo tay hoặc không kèm refresh token (ví dụ `lvyvesuscale@hotmail.com`). Hệ thống BẮT BUỘC đọc OTP thông qua ứng dụng Outlook cài sẵn trên thiết bị Android (`read_tiktok_otp_from_outlook_app`).

## 2. Xử lý Màn hình Onboarding Carousel trên Ứng dụng Outlook Trắng
Khi ứng dụng Outlook trên thiết bị chưa từng đăng nhập tài khoản nào (app trắng hoặc sau khi clear data), script login văng lỗi `STOPPED: OUTLOOK_APP_INBOX_NOT_VERIFIED` do bị kẹt ở các bước onboarding chào mừng.

Quy trình giải phóng UI & đăng nhập hòm thư Hotmail Loại 1 vào Outlook app:
1. **Màn hình Welcome Carousel**:
   - Title: *"Chào mừng bạn đến với Outlook"*
   - Tap nút *"THÊM TÀI KHOẢN"* (`com.microsoft.office.outlook:id/btn_primary_button`, bounds `[72,1404][1008,1548]`, tâm `540, 1476`).
2. **Màn hình Nhập Email**:
   - Gõ email vào `com.microsoft.office.outlook:id/auto_complete_input_email` (`bounds=[48,724][1032,874]`, tâm `540, 799`).
   - Tap nút *"TIẾP TỤC"* (`com.microsoft.office.outlook:id/btn_primary_button`, bounds `[48,1579][1032,1723]`, tâm `540, 1651`).
3. **Màn hình Chọn loại tài khoản (Account Type Selector)**:
   - Không được để trôi chọn lung tung; tap trực tiếp vào icon *"Outlook"* (`com.microsoft.office.outlook:id/btn_add_account_outlook`, bounds `[360,384][720,768]`, tâm `540, 576`).
4. **Màn hình Nhập Mật khẩu Microsoft**:
   - Tap ô `passwordEntry` (`bounds=[99,639][909,753]`, tâm `504, 696`), gõ mật khẩu Hotmail.
   - Tap nút *"Tiếp theo"* (`[72,954][1008,1068]`, tâm `540, 1011`).
5. **Màn hình "Bạn muốn thêm một tài khoản khác không?"**:
   - BẮT BUỘC tap *"CÓ LẼ ĐỂ SAU"* (`com.microsoft.office.outlook:id/bottom_flow_navigation_start_button`, bounds `[0,1764][361,1908]`, tâm `180, 1836`). Tuyệt đối không tap "THÊM".
6. **Màn hình Privacy Tour (2 bước)**:
   - Bước 1: *"Dữ liệu của bạn, theo cách của bạn"* -> tap *"TIẾP THEO"* (`com.microsoft.office.outlook:id/bottom_flow_navigation_end_button`, bounds `[692,1764][1080,1908]`, tâm `886, 1836`).
   - Bước 2: *"Nâng tầm trải nghiệm của bạn"* -> tap *"TIẾP TỤC VỚI OUTLOOK"* (tâm `886, 1836`).
7. **Xác nhận Hộp Thư Đến**:
   - Màn hình chuyển về danh sách thư `Hộp thư đến` (`HOP thur dén`). Lúc này thư xác thực chứa mã OTP 6 số từ `TikTok` sẽ tự động hiển thị để script bóc tách mã.

## 3. TikTok 2FA Authenticator & Email OTP Phối Hợp
- Khi tài khoản bật xác minh 2 bước dạng Authenticator:
  - Sinh mã bằng secret lưu trong cột 5 (2FA) của workbook: `pyotp.TOTP(secret).now()`.
  - Tap ô nhập, xóa sạch các ký tự cũ (keyevent 67), gõ mã 6 số và tap nút Xác nhận (`com.ss.android.ugc.trill:id/foa` bounds `[96,1728][984,1884]`).
- Nếu sau khi submit Authenticator mà TikTok chuyển tiếp sang đòi mã OTP gửi về Email:
  - Vào app Outlook đọc mã OTP mới nhất từ tiêu đề thư `TikTok` (ví dụ `382286 là mã gồm 6 chữ số của bạn`).
  - Gõ mã vào ô nhập OTP và submit để hoàn tất đăng nhập.

## 4. Kỷ Luật Nạp Nick Cũ & Cờ `--no-track`
- Khi login bổ sung cho tài khoản đã có sẵn trong sổ cái Master (`taikhoan_dat_v2_updated .xlsx`), BẮT BUỘC thêm cờ `--no-track`:
  ```bash
  python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <target_id> --ss --no-track
  ```
- Cờ `--no-track` giúp ngăn script cố ghi đè file Excel khi OneDrive đang khóa đồng bộ, tránh phát sinh lỗi giả `BLOCK TRACKING_WORKBOOK_WRITE_LOCKED: [Errno 9] Bad file descriptor`.
- Nghiệm thu hoàn tất đăng nhập bằng cách chụp ảnh Tab Hồ sơ (Profile) và Account Switcher, dùng WinRT OCR đọc text xác nhận tài khoản active và đủ 8/8 nick trên máy.

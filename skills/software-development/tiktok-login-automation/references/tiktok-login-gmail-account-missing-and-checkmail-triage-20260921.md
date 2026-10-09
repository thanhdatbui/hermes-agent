# Triage Lỗi Đọc OTP Gmail/Outlook Trong TikTok Login Automation (`tiktok_login_v1.py`)

## 1. Hiện Tượng 1: `STOPPED: [7c] Không lấy được OTP từ <email>@gmail.com`

### Log đặc trưng:
```text
[otp-gmail] Mở Gmail, kiểm tra account: tranngan03012004@gmail.com
[otp-gmail] account list chua thay tranngan03012004@gmail.com (attempt 1/4, expanded=N)
[otp-gmail] account list chua thay tranngan03012004@gmail.com (attempt 4/4, expanded=N)
[otp-gmail] tranngan03012004@gmail.com khong co trong Gmail account list sau retry
[7c] OTP không về -> Kiểm tra live Gmail qua checkmail.live cho tranngan03012004@gmail.com
[7c] checkmail.live check: Gmail tranngan03012004@gmail.com vẫn LIVE, TikTok không phát OTP về inbox
STOPPED: [7c] Không lấy được OTP từ tranngan03012004@gmail.com
```

### Bản chất cơ chế & Cạm bẫy (Pitfall):
1. **`checkmail.live` KHÔNG đọc được OTP**:
   - `checkmail.live` chỉ là API kiểm tra sự tồn tại (LIVE / DIE) của địa chỉ email qua giao thức SMTP probe. Nó **hoàn toàn không có quyền truy cập vào hòm thư Gmail** để đọc nội dung hay OTP.
   - Khi log ghi `TikTok không phát OTP về inbox`, đây là phán đoán sai lầm của script do fallback sang checkmail.live, **không phải do TikTok server không gửi**.
2. **Cơ chế đọc OTP Gmail của `tiktok_login_v1.py`**:
   - Script khởi chạy `com.google.android.gm/.ConversationListActivityGmail` trên thiết bị Android, tap vào Avatar góc trên bên phải `(991, 168)` để mở Account Switcher và tìm tài khoản `<email>@gmail.com`.
   - Nếu tài khoản Gmail mục tiêu **chưa từng được đăng nhập vào thiết bị**, switcher sẽ không có email đó -> Script lặp lại 4 lần rồi fail.

### Quy trình Triage O(1) ngay lập tức:
1. Chạy lệnh ADB kiểm tra danh sách tài khoản Google đã có trên máy:
   ```bash
   adb -s <serial> shell "dumpsys account | grep -i 'name=.*gmail'"
   ```
2. Nếu email mục tiêu **không xuất hiện** trong danh sách -> Xác nhận 100% máy thiếu tài khoản Google.
3. Mở file `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (hoặc `gmail_clean_v2.xlsx`) theo STT máy:
   - Cột F: Email (`<email>@gmail.com`)
   - Cột G: Mật khẩu
   - Cột E: 2FA Backup codes (8 nhóm 4 ký tự)
4. Đăng nhập tài khoản Gmail vào thiết bị (hoặc bỏ qua nick này chuyển sang nick đã có sẵn tài khoản trên máy).

---

## 2. Hiện Tượng 2: `STOPPED: OUTLOOK_APP_INBOX_NOT_VERIFIED`

### Log đặc trưng:
```text
[otp-outlook-app] Non-Gmail target -> read via Outlook/Graph
[otp-outlook-app] Mailbox không có token Graph -> fallback mở Outlook app trên thiết bị
...
STOPPED: OUTLOOK_APP_INBOX_NOT_VERIFIED
```

### Bản chất cơ chế:
1. Với email Hotmail/Outlook, script ưu tiên đọc OTP qua Microsoft Graph API (nếu tài khoản mua từ Dongvanfb có token Graph ID 57 scope `Mail.Read`).
2. Nếu mailbox không có Graph token, script buộc phải fallback mở ứng dụng **Outlook** trên thiết bị (`com.microsoft.office.outlook`).
3. Nếu ứng dụng Outlook trên thiết bị chưa được đăng nhập sẵn tài khoản Hotmail mục tiêu (hoặc đang kẹt ở màn hình Splash/Onboarding) -> Script không tìm thấy hòm thư và dừng lại với `OUTLOOK_APP_INBOX_NOT_VERIFIED`.

### Quy trình Triage O(1):
1. Chụp màn hình kiểm tra trạng thái Outlook:
   ```bash
   adb -s <serial> exec-out screencap -p > /tmp/outlook_state.png
   ```
2. Kiểm tra focus hiện tại:
   ```bash
   adb -s <serial> shell "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"
   ```
3. Nếu đang kẹt ở `com.microsoft.office.outlook.ui.onboarding.splash.SplashActivity` -> App Outlook chưa được onboard/đăng nhập tài khoản Hotmail tương ứng.

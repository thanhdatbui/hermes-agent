# Hotmail Loại 1 (Không Token) vs Loại 2 (Có Token OAuth Graph API) & Quy trình Xử lý

## 1. Bản chất Phân loại Hotmail trên Farm Taadaa

| Tiêu chí | Hotmail Loại 1 (Cũ / Legacy) | Hotmail Loại 2 (Hiện đại / boxtaikhoan) |
| :--- | :--- | :--- |
| **Dữ liệu sở hữu** | Chỉ có `email \| password` | `email \| password \| refresh_token \| client_id` |
| **Lưu trữ hệ thống** | `taikhoan_dat_v2_updated .xlsx` (cột 5, 6) | `gmail_clean_v2.xlsx` (cột 9 token, cột 10 client_id) |
| **Giao thức đọc mail PC** | **KHÔNG THỂ**. Microsoft đã chặn hoàn toàn Basic Auth IMAP/SMTP đối với tài khoản cá nhân. | **100% qua PC**. Gọi HTTP Microsoft Graph API `/me/messages` lấy OTP và Magic Link. |
| **Tác động lên điện thoại** | **BẮT BUỘC** đăng nhập vào app Outlook trên máy Android. | **TUYỆT ĐỐI CẤM** mở app Outlook trên điện thoại (để tránh sai lệch UI state). |
| **Mức độ song song** | Tuần tự từng máy (tránh tranh chấp UI & hòm thư recovery OTP dùng chung). | Song song hàng chục máy qua API từ máy tính. |

---

## 2. Quy trình Xử lý Hotmail Loại 1 (Không có Token)

Khi TikTok yêu cầu mã xác minh OTP gửi về Hotmail Loại 1 (như trường hợp `ahmiyaattikar@hotmail.com` trên Máy 32):

### Bước 1: Đăng nhập hòm thư vào App Outlook trên thiết bị
Sử dụng runner chuẩn hóa của repo `Hotmail`:
```bash
cd D:/Taadaa/Hotmail
HOTMAIL_PASSWORD="<password>" python flows/login_outlook_one_machine.py \
    --machine <MACHINE_NUM> \
    --serial <SERIAL> \
    --email <EMAIL> \
    --user-authorized
```
*Lưu ý an toàn & Pitfalls đã kiểm chứng thực tế:*
- Chạy tuần tự từng máy vì hòm thư recovery OTP (`thanhdatbui1995@gmail.com`) được dùng chung; chạy đồng thời 2 máy sẽ làm rò rỉ OTP của nhau.
- Script tự động acquire `DeviceLock` và enforce `NO-ROTATION GUARD` (khóa xoay màn hình chân dung trước khi mở Outlook).
- **Popup USB Debugging (Samsung S7)**: Khi ADB reconnect, dialog `Cho phép gỡ lỗi USB?` (`com.android.systemui:id/alwaysUse` + `android:id/button1`) có thể chặn toàn bộ flow. Phải tap checkbox `Luôn cho phép` và `OK`.
- **Interstitial "Sử dụng mật khẩu của bạn" (Use your password)**: Trên WebView Microsoft, nếu xuất hiện màn hình bảo vệ `Chúng tôi sẽ gửi mã đến th*****@gmail.com` kèm nút `Sử dụng mật khẩu của bạn` (`[288,1443][792,1494]`), bắt buộc phải tap nút này để hiển thị ô nhập mật khẩu (`passwordEntry`).
- **Gõ mật khẩu chứa ký tự đặc biệt (`!`, `$`, `#`)**: CẤM dùng `adb shell input text` thô vì shell Linux/bash sẽ nuốt hoặc làm sai ký tự `!`. Bắt buộc dùng `AdbKeyboard` broadcast mã hóa base64 (`ADB_KEYBOARD_SET_TEXT`).
- **Xử lý Mật khẩu Sai (Wrong Password Guard)**: Nếu màn hình WebView báo lỗi đỏ `Mật khẩu đó không đúng với tài khoản Microsoft của bạn`, mật khẩu lưu trữ trong bảng tính đã bị stale; dừng flow ngay và báo `OUTLOOK_APP_WRONG_PASSWORD`, chuyển sang luồng khôi phục qua recovery email `thanhdatbui1995@gmail.com` thay vì retry mù quáng.

### Bước 2: Tự động Đọc OTP qua App Outlook
Sau khi app Outlook đã có tài khoản:
- Script `tiktok_login_v1.py` sẽ phát hiện hòm thư chưa có Graph token và kích hoạt fallback:
  `[otp-outlook-app] Non-Gmail target -> read via Outlook/Graph`
  `[otp-outlook-app] Mailbox không có token Graph -> fallback mở Outlook app trên thiết bị`
- Script tự switch sang Outlook, tìm thư mới từ TikTok, bóc tách mã OTP 6 số (hoặc click nút Magic Link qua ATX click), sau đó restore task TikTok từ Recents để điền mã.

---

## 3. Quy trình Xử lý Hotmail Loại 2 (Có Token)

Khi hòm thư có `refresh_token` + `client_id`:
- Script `hotmail_provider.py` sẽ giải mã và gọi endpoint OAuth2 của Microsoft để lấy `access_token`:
  `POST https://login.microsoftonline.com/common/oauth2/v2.0/token`
- Đọc thư mới nhất trực tiếp trên PC qua:
  `GET https://graph.microsoft.com/v1.0/me/messages?$top=5`
- Trích xuất mã OTP 6 số hoặc magic link URL trong vòng < 5 giây.
- **Quy tắc bất biến:** Không bao giờ mở app Outlook trên thiết bị nếu mailbox đã có token.

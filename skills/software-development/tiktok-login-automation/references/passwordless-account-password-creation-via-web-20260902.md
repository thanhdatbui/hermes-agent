# Bẫy Khởi Tạo / Đặt Lại Mật Khẩu Cho Nick Reg Passwordless (OTP/Magic Link) và Giải Pháp Web Chrome

## 1. Bối cảnh & Vấn đề (Root Cause)
- Các tài khoản TikTok được đăng ký tự động qua Hotmail bằng cơ chế **OTP / Magic Link** (như `social_reg_v1.py`) không trải qua bước nhập mật khẩu khi tạo tài khoản.
- Cột `PASS` trong Excel lúc này là chuỗi placeholder sinh ngẫu nhiên trước khi chạy nhưng chưa từng được nạp lên server TikTok.
- Khi cần tạo mật khẩu cố định chuẩn theo Excel:
  - **Nếu thao tác trên App TikTok đang có nhiều tài khoản (Multi-Account Switcher):** Sau khi vào *Quên mật khẩu* -> nhận OTP Hotmail, TikTok phát hiện thiết bị có session tài khoản khác và chặn lại bằng màn hình WebView *"Xác minh danh tính: Xác minh đó là bạn"*, ép xác thực chéo qua Email/SĐT của tài khoản đang active trên máy (vd: `laquyen2601` -> `l***3@gmail.com`). Nếu tài khoản đó hết hạn phiên Google/Gmail, flow bị kẹt hoàn toàn.

## 2. Giải pháp Chuẩn: Khởi tạo mật khẩu qua Trình duyệt Web (Chrome)
Thực hiện luồng đặt mật khẩu trên Chrome (trên thiết bị Android hoặc qua proxy cổng 5101..5180 trên PC) để cách ly hoàn toàn khỏi session đa tài khoản của app TikTok.

### Quy trình từng bước:
1. **Mở Chrome vào trang Đăng nhập TikTok:**
   ```bash
   adb -s <SERIAL> shell "am start -n com.android.chrome/com.google.android.apps.chrome.Main -d 'https://www.tiktok.com/login/phone-or-email/email'"
   ```
2. **Chọn Quên mật khẩu qua Email:**
   - Tap text *"Bạn quên mật khẩu?"* (`bounds: [96,963][984,1017]` -> tâm `(540, 990)`).
   - Bottom sheet hỏi phương thức -> tap *"Email"* (`bounds: [108,1122][972,1266]` -> tâm `(540, 1194)`).
3. **Nhập Email & Gửi mã OTP:**
   - Trang chuyển sang `tiktok.com/login/email/forget-password` (*"Nhập địa chỉ email"*).
   - Nhập email (vd: `LyndiaSchlesinger2198@hotmail.com`), ẩn bàn phím (`input keyevent 111`), tap nút *"Gửi mã"* (`(540, 963)`).
4. **Lấy & Nhập mã OTP 6 số:**
   - Đọc OTP 6 số từ Hotmail qua XOAUTH2 token (`login.microsoftonline.com` + IMAP `outlook.office365.com:993`) hoặc Microsoft Graph API.
   - Nhập 6 số vào trường mã xác thực trên web (`tiktok.com/login/reset/email/digit-code`).
5. **Đặt mật khẩu mới:**
   - Web chuyển thẳng tới `tiktok.com/login/reset/password` (*"Đặt lại mật khẩu: 8 đến 20 ký tự, các chữ cái, số và ký tự đặc biệt"*).
   - Nhập mật khẩu chuẩn từ cột `PASS` trong Excel (vd: `0vjTtaET@kF`), ẩn bàn phím, tap *"Đăng nhập"* (`(540, 1041)`).
   - Web hiển thị thông báo popup **`Đã đăng nhập`** -> Mật khẩu được kích hoạt thành công trên toàn hệ thống TikTok.

## 3. Quy tắc kiểm tra khi thiết bị sụt áp / lỏng cáp
- Khi phát lệnh mở app nặng (TikTok/Chrome) mà thiết bị đột ngột rớt ADB (`error: closed` / `device not found`):
  - Chờ máy reconnect trong 15-30s.
  - Kiểm tra `uptime` và pin: `adb -s <SERIAL> shell "uptime; dumpsys battery | grep level"`.
  - Nếu `uptime` < 2 phút -> máy vừa bị reboot cứng do sụt áp nguồn/pin ảo hoặc lỏng cáp USB.
  - Sau reboot, khởi chạy lại service ATX ngầm: `adb shell "/data/local/tmp/atx-agent server -d" && adb forward tcp:7912 tcp:7912`.

# Bài học & Pitfalls: Bật 2FA Google Authenticator (S7 On-Device vs GPM Profile)

## 1. Bản chất phân tầng Session của Google
- **Native Android App Session**: 
  - Token OAuth di động trên Samsung S7 cấp quyền đồng bộ mail (app Gmail), danh bạ, TikTok SSO.
  - Nhưng tính năng **"Xác minh 2 bước" (2-Step Verification)** không chạy native mà mở **cửa sổ WebView bảo mật**.
  - Cửa sổ WebView này là một phiên mới hoàn toàn (không có cookie web trước đó), khi duyệt qua IP Proxy farm sẽ kích hoạt ngay cơ chế **reCAPTCHA xác minh danh tính** hoặc màn hình chặn *"Google không thể xác minh rằng tài khoản này là của bạn"*.
  - Trên điện thoại Android qua ADB, **không có extension giải captcha âm thanh** -> luồng bật 2FA trên S7 qua ADB UI sẽ bị Google chặn đứng ở WebView.

## 2. Vì sao thực hiện qua GPM Profile lại thành công?
- **Web Browser Session hoàn chỉnh**: Profile GPM Chrome lưu đầy đủ chuỗi cookie web chuẩn (`SID`, `SSID`, `HSID`, `__Secure-3PSID`...) cùng Fingerprint PC ổn định.
- **Có module vượt challenge tự động**: Script Playwright trên GPM (`run_add_2fa_remaining.py`) được trang bị:
  - Tự động điền mật khẩu khi gặp `challenge/pwd`.
  - Giải reCAPTCHA âm thanh tự động qua `solve_recaptcha_audio`.
  - Tự bóc chuỗi Secret Key Base32 (32 ký tự), tính TOTP True UTC qua `pyotp` và điền xác nhận.
- Kết quả: Khi tài khoản đã login sống trên GPM, việc kích hoạt 2FA thành công 100%.

## 3. Quy chuẩn cấu hình Watchdog / Batch Worker
- **Tối đa Workers**: Luôn bọc `ThreadPoolExecutor(max_workers=30)` khi duyệt danh sách máy/profile để tránh nghẽn luồng tuần tự kéo dài hàng giờ dẫn đến Hermes timeout (10,800s).
- **Timeout cứng cho ADB Subprocess**: Toàn bộ các lệnh gọi ADB (`tap`, `keyevent`, `swipe`, `am start`) bắt buộc phải có `timeout=10` để tránh trường hợp điện thoại bị đơ ADB shell làm block vĩnh viễn tiến trình cha.
- **Đồng bộ 3 tầng**: Khi cập nhật watchdog script, bắt buộc đồng bộ đồng thời 3 nơi:
  1. `C:\Users\Kibe\AppData\Local\hermes\scripts\` (Local runtime)
  2. `D:\Taadaa\Hermes\deploy\hermes-home\scripts\` (Git deploy repo)
  3. `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\` (OneDrive shared)

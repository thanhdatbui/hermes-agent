# Privy Auth & App Automation via ADB (React Native & Mobile Apps)

## 1. Bản chất kiến trúc Privy Auth trên Android
- Các app Web3 / Social / Airdrop (như Phygitals `com.phygitals.mobile`) sử dụng SDK **Privy Auth** để quản lý đăng nhập và tự động tạo ví Embedded Wallet (thường là Solana / Ethereum).
- Giao diện Privy hiển thị các tùy chọn: Email, Phone, Google OAuth, Apple Sign-in.
- Khi chọn **Email Auth**, Privy gửi mã OTP 6 số qua email (`no-reply@mail.privy.io`).

## 2. Cạm bẫy nhập liệu (Text Input) với AdbKeyboard vs Samsung Keypad
- **Vấn đề trôi text / nuốt ký tự đuôi:**
  - Ô nhập email trên WebView/React Native của Privy dễ bị nuốt ký tự cuối (ví dụ gõ `.com` bị rơi mất chữ `m` thành `.co` hoặc `comm`).
  - Lệnh `adb shell am broadcast -a ADB_CLEAR_TEXT` của `com.github.uiautomator/.AdbKeyboard` trên một số trường Input WebView có thể xóa sạch ô nhập hoặc không ăn focus đúng cách nếu IME chưa bật.
- **Quy tắc xử lý:**
  1. Khi dùng bàn phím mặc định (Samsung Keypad): Gõ ký tự cuối riêng hoặc kiểm tra WinRT OCR text thật trong ô trước khi bấm submit.
  2. Khi ẩn bàn phím để lộ nút bấm: Dùng `adb shell input keyevent 4` (KEYCODE_BACK) một lần để ẩn bàn phím ảo, không làm thoát Activity.

## 3. Quy trình bắt OTP tự động không mua mail mới
- **Tận dụng kho mail farm có sẵn:**
  - Kiểm tra `gmail_clean_v2.xlsx`: Có sẵn hàng trăm tài khoản Hotmail và Gmail.
  - **Hotmail có Graph API Token:** Sử dụng `resolve_graph_credentials(email)` và `exchange_refresh_token(token, cid)` từ `D:/Taadaa/Tiktok_Reg/hotmail_provider.py` để đọc inbox/junkemail qua Microsoft Graph API mà không cần mở app.
  - **Gmail IMAP Standard:** Nếu tài khoản Gmail quản lý có cấu hình App Password (`OTP_MAIL_APP_PASSWORD`), truy vấn trực tiếp cổng `imap.gmail.com:993` với `imaplib` để lấy mã code 6 số từ `no-reply@mail.privy.io` trong vòng < 5 giây.
- **Nhập mã OTP 6 số:**
  - Màn hình Privy Auth chia thành 6 ô số và mở sẵn bàn phím số (Numeric Keypad).
  - Sử dụng toạ độ bàn phím số chuẩn (ví dụ trên Samsung S7 độ phân giải 1080x1920):
    - Hàng 1 (1, 2, 3): y ≈ 1266
    - Hàng 2 (4, 5, 6): y ≈ 1444
    - Hàng 3 (7, 8, 9): y ≈ 1620
    - Hàng 4 (0): x ≈ 409, y ≈ 1800
  - Tap lần lượt 6 số với độ trễ `time.sleep(0.4)`. Privy tự động verify ngay khi đủ 6 ký tự mà không cần bấm Enter.

## 4. Xác minh sau đăng nhập (Verification & Gate 6)
- **Kiểm tra trạng thái ví:** Màn hình chính xuất hiện header số dư (`$0.00`) và menu điều hướng (Packs, Collection, Offers, Rewards, Profile).
- **Embedded Wallet:** Kiểm tra mục Wallet/Settings để lấy địa chỉ ví Solana đã tạo và kiểm tra chức năng rút tiền (USDC/USDT mạng Solana, yêu cầu nạp tối thiểu 0.005 SOL làm phí gas).
- **Mã Referral / Attribution:** Tab Rewards hiển thị mã code mời và link AppsFlyer OneLink.

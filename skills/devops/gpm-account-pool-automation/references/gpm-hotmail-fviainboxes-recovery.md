# Hotmail Change Info & fviainboxes Recovery Mail OTP via GPM Profile

Khi thực hiện đổi mật khẩu Hotmail trên GPM Profile:
1. Microsoft yêu cầu xác minh bảo mật qua email khôi phục (thường có domain dạng `@fviainboxes.com`).
2. Mở tab mới ngay trong chính browser instance của profile đó: `https://fviainboxes.com/`.
3. Nhập username (phần trước `@fviainboxes.com`) và bấm `Get Email`.
4. Endpoint REST API đọc hộp thư:
   `GET https://fviainboxes.com/messages?username={username}&domain=fviainboxes.com`
   `GET https://fviainboxes.com/message?username={username}&domain=fviainboxes.com&id={id}`
5. Bốc mã OTP trả về từ Microsoft và điền vào form đổi mật khẩu.

# Pitfalls: Web OAuth Login, React Encrypted Passwords & Public Free Proxy Geoblock

## 1. Cơ chế Meta/Facebook Encrypted Password (`enc_password`)
- **Hiện tượng:** Khi sử dụng automation (Playwright/Selenium) điền UID/Email và mật khẩu vào form đăng nhập Web Facebook (`facebook.com/login` hoặc OAuth popups của Meta), Facebook báo lỗi *"Bạn đã nhập sai thông tin đăng nhập"* mặc dù thông tin tài khoản hoàn toàn chính xác.
- **Nguyên nhân:** Meta sử dụng React frontend với cơ chế mã hóa mật khẩu client-side (`#pwd_...` / `enc_password`). Các lệnh `.fill()` hoặc script submit form giả lập không kích hoạt đúng event handler mã hóa khóa công khai của Meta, khiến payload gửi lên server mang mật khẩu rỗng hoặc sai hash.
- **Xử lý:** 
  - Ưu tiên nạp Cookie Web hợp lệ (`c_user`, `xs`, `fr`, `datr`).
  - Đối với account mua tạo từ Android App (App Session), cookie app không tương thích trực tiếp với Web (`400 Bad Request` -> `c_user=deleted`), bắt buộc phải chuyển giao diện cho người dùng đăng nhập tay trên GPM hoặc dùng cơ chế login OAuth WebView app-native.
  - CẤM loop thử lại điền mật khẩu liên tục làm khóa checkpoint nick.

## 2. Rủi ro của Public SOCKS5/Free Proxy khi vượt Geoblock & OAuth
- **Hiện tượng:** Proxy free/public quét từ các repo GitHub / Free list có thể vượt qua geoblock ban đầu (như Muse AI `/access/verification`), nhưng sau 2-3 phút thì băng thông nghẽn hoặc rớt kết nối (`Timeout 25s`).
- **Hậu quả:** Khi đang trong luồng OAuth nhạy cảm (Meta SSO, Instagram Verify), việc rớt kết nối giữa chừng làm Meta kích hoạt lại cơ chế kiểm tra vị trí/IP gốc, dẫn đến việc bị đẩy ngược về màn hình chờ (Waitlist) hoặc khóa luồng xác minh.
- **Kỷ luật:** Đối với các tác vụ yêu cầu xác minh danh tính / OAuth liên tục nhiều bước trên IP ngoại, BẮT BUỘC sử dụng **Proxy Residential/Private có user:pass ổn định**, không dùng proxy public cào trên mạng để chạy quy trình liên kết tài khoản.

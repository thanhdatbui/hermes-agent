# Microsoft Security Flow via GPM CDP & fviainboxes OTP Automation

## 1. Bối cảnh & Mục đích
Tự động hóa hoàn toàn quy trình đổi mật khẩu Hotmail và quản lý bảo mật thông qua Playwright CDP kết nối trực tiếp vào GPMLogin Profile (Chromium core 142), thay thế hoàn toàn điện thoại Android S7.

## 2. Các chướng ngại vật (Interstitials) & Cách xử lý tự động

### 2.1. Màn hình xác minh danh tính qua Mail Khôi phục (Proof / 2FA Challenge)
- **Cơ chế Microsoft**: Khi vào trang `https://account.live.com/password/change`, Microsoft thường bắt xác minh danh tính bằng cách gửi mã tới mail khôi phục (dạng hint: `vi*****@fviainboxes.com`).
- **Tra cứu Mail Khôi Phục**: Mail khôi phục gốc nằm tại cột 5 (`mail khôi phục`) của sheet `Tài Khoản` trong `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
- **Form UI Mới**:
  * Input nhập email xác nhận: `#proof-confirmation-email-input`.
  * Nút gửi mã: `button:has-text('Gửi mã')` hoặc `button:has-text('Send code')`.
  * Giao diện nhập mã: 6 ô input độc lập `#codeEntry-0`, `#codeEntry-1`, ..., `#codeEntry-5`.
- **Bốc mã OTP từ API fviainboxes.com**:
  * Endpoint danh sách tin nhắn: `GET https://fviainboxes.com/messages?username=<user>&domain=fviainboxes.com`
  * Endpoint chi tiết: `GET https://fviainboxes.com/message?username=<user>&domain=fviainboxes.com&id=<mid>`
  * Trích xuất mã OTP: Microsoft gửi mã dạng text hoặc span. Cần regex cả `Security code: <span...>(\d{6,7})</span>` và `Your single-use code is: (\d{6,7})`.
  * Điền lần lượt 6 ký tự vào `#codeEntry-0..5` với delay 0.2s giữa các ô.

### 2.2. Màn hình cập nhật điều khoản (Terms Update) & Thông báo
- Màn hình *"Chúng tôi đang cập nhật các điều khoản của mình"* / *"Ghi chú nhanh về tài khoản Microsoft"*:
  * Bấm nút: `button:has-text('Tiếp theo')`, `button:has-text('Tiếp tục')`, hoặc `button:has-text('Next')`.

### 2.3. Duy trì đăng nhập? (KMSI - Keep Me Signed In)
- Màn hình *"Duy trì đăng nhập?"*:
  * Bắt buộc bấm **"Có"** (`button:has-text('Có')`, `button:has-text('Có')`, `button:has-text('Yes')`) để lưu session cookie vào profile GPM, tránh bị bắt đăng nhập lại ở các bước sau.

### 2.4. Đổi mật khẩu (Password Change)
- URL: `https://account.live.com/password/change`
- Trường nhập mật khẩu: `#iPassword` (Mật khẩu mới) và `#iRetypePassword` (Nhập lại mật khẩu).
- Nút submit: `#UpdatePasswordAction` (hoặc `input[value='Lưu']`, `button:has-text('Lưu')`).

## 3. Quản lý bảo mật & Đăng xuất khỏi mọi nơi (Sign out everywhere)
- URL: `https://account.live.com/proofs/manage/additional`
- **Gỡ mail khôi phục rác**: Kiểm tra danh sách untrusted domains của bên bán (`getnada`, `smvmail`, `tempmail`...) và click nút Xóa nếu có.
- **Sign out everywhere**:
  * Nút nằm ở cuối trang: `a:has-text('Đăng xuất khỏi mọi nơi')` hoặc `button:has-text('Đăng xuất khỏi mọi nơi')`.
  * Cuộn trang xuống đáy (`window.scrollTo(0, document.body.scrollHeight)`).
  * Chụp ảnh cận cảnh (crop zoom) chứng minh nút "Đăng xuất khỏi mọi nơi" để trả về bằng chứng thị giác trực quan cho người dùng.

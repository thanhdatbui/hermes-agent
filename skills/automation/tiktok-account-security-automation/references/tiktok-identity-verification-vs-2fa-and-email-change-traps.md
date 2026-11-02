# TikTok 2FA vs Identity Verification in Email Change Flow

## 1. Bản Chất Phân Quyền Bảo Mật TikTok
Trên app TikTok Android, cơ chế bảo mật chia làm 2 flow hoàn toàn độc lập:

1. **Login Flow (Đăng Nhập Thiết Bị Mới):**
   - Kích hoạt cơ chế **`Xác minh 2 bước` (2FA / Two-Factor Authentication)**.
   - Các phương thức hỗ trợ: SMS (Điện thoại), Email, Ứng dụng xác thực (Authenticator / TOTP - Duo Mobile, Google Authenticator), Mật khẩu.
   - Có tùy chọn **`Sử dụng phương thức khác >`** cho phép dùng TOTP secret key để bypass nếu không có SIM/Mail.

2. **Credential Modification Flow (Thay Đổi / Hủy Liên Kết Email, SĐT):**
   - Kích hoạt cơ chế **`Xác minh danh tính - Xác minh để là bạn` (Identity Verification)**.
   - **Đặc điểm sống còn:** TikTok **KHÔNG CHO PHÉP** sử dụng Ứng dụng xác thực (Authenticator / TOTP) trên màn hình này, kể cả khi trong mục *Bảo mật & quyền* -> *Xác minh 2 bước*, dòng *Ứng dụng xác thực* đã hiển thị `Bật` và đang có key live.
   - **Kênh xác minh bắt buộc:**
     - Nếu nick **chưa liên kết SĐT**: Phương thức hiển thị duy nhất là gửi mã OTP về chính Email đang liên kết hiện tại (Gmail DIE cũ).
     - Nếu có dòng *Mật khẩu* (như một số nick): Cho phép nhập mật khẩu TikTok, nhưng sau đó TikTok vẫn có thể kiểm tra độ tin cậy của thiết bị/phiên nuôi để quyết định có mở form đổi email hay không.
     - Nút *Yêu cầu hỗ trợ*: Chỉ mở form Ticket hỗ trợ khách hàng (*TikTok Support - Send a message...*), không dẫn tới form nhập mã 2FA.

## 2. Quy Trình Kiểm Tra Trạng Thái 2FA Thật Trên Thiết Bị
Khi cần kiểm chứng một tài khoản đã bật 2FA hay chưa, cấm đoán mò qua màn hình đổi email. Bắt buộc điều hướng:
1. `Hồ sơ` (972, 1881) -> `Menu 3 gạch` (1005, 150) -> `Cài đặt và quyền riêng tư` (530, 1260).
2. Cuộn xuống mục **`Tài khoản`** -> chọn **`Bảo mật & quyền`** (350, 590).
3. Đọc dòng **`Xác minh 2 bước`**:
   - Nếu hiển thị `Bật >`: Bấm vào để xem chi tiết 4 mục (*Điện thoại*, *Email*, *Ứng dụng xác thực*, *Mật khẩu*).
   - Nếu *Ứng dụng xác thực* có nút `Bật`: Bấm vào sẽ mở popup *Trình xác thực - Bạn hiện đang sử dụng ứng dụng xác thực này để tạo mã xác minh* (Cập nhật / Xóa). Đây là bằng chứng 100% 2FA TOTP đã được setup.

## 3. Pitfall & Fail-Safe Khi Thay Đổi Email
- **Bẫy lặp vô tận (Loop Trap):** Khi worker vào form đổi email và bị chặn bởi màn hình *Xác minh danh tính* (chỉ có tùy chọn Gmail DIE cũ):
  - Bắt buộc kiểm tra OCR: Nếu thấy `xác minh danh tính` hoặc `xác minh để là bạn` mà KHÔNG có form nhập email mới:
  - **DỪNG NGAY**, không được tiếp tục gọi hàm `get_clean_hotmail()` và không gọi Graph API rút OTP Hotmail. Việc cố rút OTP Hotmail trong khi app đang ở màn hình đòi OTP Gmail cũ sẽ gây lỗi `khong lay duoc OTP` hàng trăm lần và làm cạn kiệt tài nguyên / khóa giữ tạm Hotmail trong kho (`HOLD_CHANGE`).

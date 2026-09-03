# TikTok Login OTP Verification: Gmail Conversation Thread Grouping & Account Suspended Handling (2026-08-28)

## 1. Hiện tượng & Bối cảnh (Máy 71)
- **Triệu chứng ban đầu:** Feed runner dừng phiên với mã lỗi `manual-needed:account-switcher-missing-expected` do nick `hanh.duong.11.22` thiếu trên thiết bị.
- **Tiến trình đăng nhập lại:**
  1. Mở TikTok -> tab Hồ sơ -> Account Switcher -> Thêm tài khoản -> Email/TikTok ID: `duonghanh270320033@gmail.com`.
  2. TikTok gửi mã OTP / Magic link về Gmail.

## 2. Các cạm bẫy & Giải pháp kỹ thuật

### Bẫy 1: Gmail Conversation Thread Grouping (Gom nhiều email cùng thread)
- **Hiện tượng:** Khi tài khoản Gmail đã từng nhận nhiều email mã xác minh của TikTok (từ các ngày trước, ví dụ `22 Th7` hoặc các lần resend trước), Gmail tự động gom các email thành một conversation thread duy nhất.
- **Hậu quả:** Hàm đọc Gmail nếu chỉ đọc snippet/preview dòng đầu hoặc mở email ở phần đầu thread sẽ đọc trúng mã cũ (ví dụ `149954` của tháng trước) -> TikTok báo `Lỗi mã xác minh email`.
- **Xử lý chuẩn:**
  1. Trước khi lấy mã: Bắt buộc gọi pull-to-refresh (swipe down 540,600 -> 540,1500) ở màn hình Inbox list.
  2. Mở thread TikTok mới nhất (kiểm tra timestamp trùng khớp với thời điểm gửi).
  3. Cuộn xuống cuối thread (`swipe 540 1500 540 500`) để đọc tin nhắn con mới nhất hoặc lấy mã từ khối text mới nhất nằm ở đáy thread.
  4. Trong email có nút đỏ **"Đăng nhập"** (Magic Link intent `[168,750][930,897]`) -> có thể tap trực tiếp nút này để kích hoạt mở TikTok đăng nhập thẳng mà không cần nhập số thủ công.

### Bẫy 2: Xoay màn hình Landscape trên S7
- **Hiện tượng:** Thiết bị có thể bị chuyển sang chế độ màn hình ngang (Landscape `1920x1080`) do app Gmail hoặc service xoay màn hình.
- **Khắc phục:** Luôn khoá xoay dọc trước và sau khi tương tác:
  ```bash
  adb shell "settings put system accelerometer_rotation 0 && settings put system user_rotation 0"
  ```

### Bẫy 3: Xử lý phản hồi `Tài khoản của bạn đã bị đình chỉ.` (Account Suspended)
- **Dấu hiệu:** Sau khi submit đúng mã OTP mới nhất, TikTok không chuyển vào Home Feed mà hiển thị text lỗi: `Tài khoản của bạn đã bị đình chỉ.`
- **Quy trình kết luận & Báo cáo:**
  1. Chụp ảnh màn hình thực tế (screencap) lưu file local và gửi bằng cú pháp `MEDIA:<path>` dòng riêng cho user.
  2. Dọn dẹp màn hình thiết bị về Home (keyevent 4 x3 + keyevent 3) để tránh kẹt màn hình lỗi cho các phiên sau.
  3. Kết luận tài khoản đã bị TikTok ban/đình chỉ, báo cáo rõ ràng blocker để user cập nhật thay thế nick mới trong workbook.

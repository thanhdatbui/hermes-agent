# S7 Gmail Registration: Switcher Boundary & Visual Evidence Timing

## 1. Bento Card Fallback Boundary Trong Switcher
- **Hiện tượng:** Hàm `find_add_account_card_in_switcher()` có fallback bento card `if 300 <= y <= 1850 and x <= 700`.
- **Cạm bẫy:** Trên Samsung S7, card header tài khoản đang active và avatar nằm tại y = 336 (bounds `[408,204][672,468]`). Fallback quét trúng node y=336, tap trúng avatar gây mở *"Thêm ảnh hồ sơ"* hoặc tap trúng tài khoản cũ bị checkpoint phiên khiến Google Play Services bung popup *"Hoàn tất đăng nhập để tiếp tục"*.
- **Chuẩn hóa:** Đặt ngưỡng chặn cứng `700 <= y <= 1850` để loại trừ hoàn toàn khu vực header active profile (y < 700), buộc runner phải cuộn danh sách lên để bấm đúng nút *"Thêm tài khoản khác"*.

## 2. Bắt Lỗi Google Signup Lifecycle & Transport Error
- **Hiện tượng:** Khi tạo account, WebView của Google trả về lỗi rớt mạng/proxy:
  `Error code = 7, Path = .../AccountLifecyclePlatformSignupUi/data/batchexecute, HTTP status = 0 (XHR Error Code: 6)`.
- **Chuẩn hóa:** Gọi `is_google_transport_or_lifecycle_error_xml(xml)` ở cả Bước 10 (Password) và Bước 11 (Review). Khi phát hiện, raise `[GOOGLE_TRANSPORT_ERROR]` để phân loại chính xác lỗi hạ tầng/mạng thay vì rơi vào `[10_pass]` hay `[11_review]`.

## 3. Bẫy Timing Chụp Ảnh Nghiệm Thu Sau Bước Password (Visual Evidence Timing Trap)
- **Hiện tượng:** Ngay sau khi bấm nút *Tiếp theo* ở Bước 10 (Password), màn hình chuyển cảnh hiển thị spinner xoay vòng: *"Google — Quá trình này có thể mất vài phút..."*.
- **Cạm bẫy:** Script chụp ảnh ngay thời điểm bấm Next (`03_10_pass_next_attempt1_*.png`), dẫn đến ảnh lưu lại là màn hình loading tạm thời. Nếu Coordinator gửi ảnh này làm bằng chứng nghiệm thu thì sẽ bị User bắt bẻ ngay: *"Gì v màn này đang load mà?"*.
- **Quy tắc bất biến:**
  1. Không lấy ảnh spinner làm bằng chứng nghiệm thu: Màn hình *"Quá trình này có thể mất vài phút..."* chỉ là trạng thái trung gian, KHÔNG phản ánh kết quả thực tế.
  2. Chờ hết polling loop: Phải đợi sau 8-15s khi Google load xong hoàn toàn màn hình đích (`phone_verify_*.png` hoặc `review_*.png`).
  3. Soi mắt qua vision: Phải kiểm tra kỹ thanh trạng thái, tiêu đề và nội dung để xác nhận màn hình đã render xong hoàn toàn trước khi gửi thẻ `MEDIA:`.

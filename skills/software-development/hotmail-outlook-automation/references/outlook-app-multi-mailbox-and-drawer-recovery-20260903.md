# Outlook App Multi-Mailbox Switching & Drawer-Open Recovery (2026-09-03)

## Bối cảnh & Hiện tượng
Khi đọc mã OTP/Magic Link TikTok từ ứng dụng Microsoft Outlook trên điện thoại Android (dành cho mailbox không có token Graph API hoặc chạy fallback thiết bị):
1. **Lỗi Drawer mở sẵn lúc khởi động**: Khi mở app Outlook, thanh ngăn điều hướng bên trái (Navigation Drawer) đã mở sẵn từ phiên trước. Trình đọc OTP kiểm tra `_outlook_app_folder_surface_visible(xml)` bị thất bại vì toolbar bị che khuất bởi Drawer, dẫn đến ném lỗi `OUTLOOK_APP_INBOX_NOT_VERIFIED` thay vì điều hướng tap vào "Hộp thư đến".
2. **Lỗi không nhận diện/chuyển đổi Mailbox khi đăng nhập nhiều tài khoản**: Một thiết bị có thể đăng nhập nhiều email Microsoft/Hotmail. Outlook chỉ hiển thị 1 mailbox active trên header drawer (`drawer_header_summary`), các mailbox còn lại hiển thị dưới dạng icon/avatar ở thanh bên trái (left rail, `bounds[0] < 250`). Trình đọc cũ chỉ kiểm tra `drawer_header_summary`, nếu tài khoản active là email khác (ví dụ `DebiDenbesten...`), script báo email mục tiêu (`valexmonyabr...`) vắng mặt hoặc ném `OUTLOOK_APP_INBOX_NOT_VERIFIED` thay vì bấm chuyển sang mailbox mục tiêu.

## Giải pháp triển khai trong `D:\Taadaa\Hotmail\flows\hotmail_login.py`

1. **Nhận diện Drawer mở sẵn trên màn hình**:
   - Thêm `_outlook_app_drawer_open(value)` vào điều kiện `wait_for` khi mở app Outlook.
   - Khi `_outlook_app_drawer_open(xml)` là True, cho phép tiếp tục flow và gọi `_outlook_app_open_inbox_from_archive`, trong đó đã có sẵn logic tap mục "Hộp thư đến" (`drawer_item_title` = "Hộp thư đến") khi drawer đang mở.

2. **Tự động chuyển đổi Mailbox mục tiêu trên Drawer Left Rail**:
   - Khi mở Navigation Drawer, nếu `drawer_header_summary` chưa khớp `target_email`, quét tìm node trong Drawer có `content-desc` hoặc `text` khớp `target_email` và tọa độ x < 250 (`bounds[0] < 250`).
   - Tap vào tọa độ icon mailbox đó trên thanh bên trái để chuyển active mailbox sang `target_email`.
   - Chờ Drawer/Toolbar cập nhật sang `target_email` và hoàn tất vào "Hộp thư đến".

3. **Trích xuất OTP an toàn**:
   - Chỉ đọc mã 6 chữ số từ email có người gửi hoặc tiêu đề liên quan đến TikTok nhận trong thời gian gần nhất, tránh đọc nhầm mã cũ từ các email trước.

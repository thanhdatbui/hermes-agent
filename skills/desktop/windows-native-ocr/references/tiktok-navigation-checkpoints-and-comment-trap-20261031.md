# TikTok Navigation Checkpoints & Comment Trap vs Account Deletion Safety (2026-10-31)

## Bối Cảnh Sự Cố & Lỗ Hổng Điều Hướng UI
Trong phiên làm việc ngày 31/10/2026, khi tự động hóa thay đổi email TikTok liên kết trên cụm máy Samsung S7/S8 (Host Windows 10, WinRT OCR), hệ thống đã gặp 2 lỗi nghiêm trọng:
1. **Lỗi 1 (Màn hình Xóa / Hủy kích hoạt tài khoản):** Script tự chế dùng tọa độ pixel cứng `[540, 1810]` sát đáy màn hình trong menu Tài khoản. Tọa độ này bấm trúng ngay dòng "Hủy kích hoạt hoặc xóa tài khoản".
2. **Lỗi 2 (Bẫy Comment Modal / Lạc luồng từ Home Feed):** Script quét OCR tìm chữ `Email` / `Tôi` / `Hồ sơ` ngay từ màn hình video Feed chính mà không điều hướng tuần tự. Kết quả là bot bấm nhầm vào khu vực bình luận của video, bật popup `227 bình luận` (Comment Bottom Sheet) che khuất toàn bộ màn hình, dẫn đến việc báo cáo sai và không bao giờ vào được form Cài đặt.

---

## 5 Checkpoints Bắt Buộc Khi Điều Hướng Vào Cài Đặt / Email TikTok

CẤM TUYỆT ĐỐI tìm kiếm mù bằng OCR từ Home Feed. Mọi automation điều hướng vào Cài đặt tài khoản BẮT BUỘC tuân thủ tuần tự 5 Checkpoints cơ học:

### Checkpoint 1: Xác Định Đúng Trang Hồ Sơ (Profile Tab)
- Từ màn hình chính TikTok, bấm nút cứng tab **Hồ sơ** ở góc dưới cùng bên phải:
  - Tọa độ chuẩn 1080x1920: `(972, 1860)`
- Đợi 2.0s và kiểm tra màn hình đã chuyển về Profile (xem avatar, username hoặc icon menu 3 gạch).

### Checkpoint 2: Mở Menu 3 Gạch (Settings Drawer)
- Tại trang Profile, bấm nút menu 3 gạch ở góc trên cùng bên phải:
  - Tọa độ chuẩn 1080x1920: `(1005, 150)`
- Đợi 2.0s để bottom sheet menu bung lên từ đáy màn hình.

### Checkpoint 3: Quét WinRT OCR Tìm "Cài Đặt Và Quyền Riêng Tư"
- Chụp ảnh màn hình (`screencap`) và gọi WinRT OCR (`ocr_screen_boxes` / `extract_ui`).
- Tìm cụm từ `Cài đặt và quyền riêng tư` hoặc `Cài đặt` / `Settings`.
- Tap vào đúng tâm bounds do WinRT OCR trả về (`hit.center`). CẤM click pixel dự đoán.

### Checkpoint 4: Quét WinRT OCR Tìm "Tài Khoản" (Fail-Safe Kèm Theo)
- Tại màn hình *Cài đặt và quyền riêng tư*, quét tìm text `Tài khoản` / `Account`.
- Tap vào tâm bounds của text `Tài khoản`.
- **CẤM TUYỆT ĐỐI:** Không bao giờ tap vào tọa độ đáy `y >= 1750` hoặc `[540, 1810]`.
- **FAIL-SAFE CHỐNG XÓA NICK:** Nếu phát hiện bất kỳ chuỗi text nào chứa:
  `['xóa tài khoản', 'hủy kích hoạt', 'xoa tai khoan', 'huy kich hoat', 'delete account', 'deactivate']`
  $\longrightarrow$ Lập tức gọi lệnh `KEYEVENT_BACK` (phím 4) thoát ra ngay và abort tiến trình!

### Checkpoint 5: Vào "Thông Tin Tài Khoản" $\rightarrow$ "Email" $\rightarrow$ "Thay Đổi Email"
- Quét WinRT OCR tìm text `Thông tin tài khoản` $\rightarrow$ Tap tâm.
- Quét text `Email` $\rightarrow$ Tap tâm.
- Quét text `Thay đổi email` $\rightarrow$ Tap tâm.
- Xác nhận màn hình hiển thị ô input `Nhập email của bạn` mới được phép tiến hành nhập email và polling OTP.

---

## Xử Lý Bẫy Comment Sheet & WebView
- Nếu màn hình xuất hiện popup bình luận (`bình luận`, `comment`, icon `✕` đóng ở góc phải): Bấm nút `Back` hoặc tap vào `✕` `(990, 680)` để đóng modal, sau đó bấm lại tab Hồ sơ `(972, 1860)` để tái đồng bộ trạng thái.

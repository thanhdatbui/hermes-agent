# TikTok OTP Throttling Detection & Auto-Replacement Flow

## 1. Hiện Tượng & Dấu Hiệu (Signature)
Khi TikTok đăng nhập tài khoản bằng email qua luồng OTP:
- Trên điện thoại (Samsung Galaxy S7): TikTok hiển thị màn hình `Xác minh email: Sử dụng liên kết này hoặc nhập mã được gửi đến <email>`.
- Kịch bản tự động bấm **Gửi lại mã** (Resend code) sau 60s đếm ngược.
- Trên hộp thư web (Outlook qua GPM CDP hoặc Graph API):
  * Session hòm thư hoàn toàn sạch, đang mở ở Inbox và Junk Email.
  * Trong suốt 120s–300s, không hề có bất kỳ email nào mới từ TikTok gửi về.
  * Chỉ tồn tại các email cũ từ các đợt xác minh trước đó (cách đây vài tuần/tháng).
- **Kết luận chẩn đoán**: TikTok đã kích hoạt cơ chế **OTP Throttling / Blacklist** trên tài khoản hoặc dải IP máy, từ chối phát OTP mới về hòm thư.

## 2. Kỷ Luật Xử Lý & Tránh Đóng Băng Dàn Farm (Anti-Insanity)
- Khi phát hiện TikTok không gửi OTP sau 1 lần bấm Gửi lại mã (resend) và hòm thư đã được kiểm tra trực tiếp là không có thư mới:
  * **CẤM TUYỆT ĐỐI**: Chạy vòng lặp ngầm thử lại liên tục trên tài khoản bị nghẽn (vi phạm Gate 6).
  * **CẤM TUYỆT ĐỐI**: Đóng băng cả dàn máy hoặc dừng ca chạy chờ đợi thủ công.
- **Quy trình thay thế tài khoản (Account Replacement) chuẩn**:
  1. Kiểm tra trạng thái máy trên dàn: Xác định các ca nuôi khác trên máy (`Tik1` đến `Tik8`) có nick hoạt động bình thường không.
  2. Tra cứu workbook tài khoản (`taikhoan_run_safe.xlsx` và `taikhoan_dat_v2_updated .xlsx`):
     * Nếu tài khoản lỗi chỉ nằm ở 1 ca riêng biệt (ví dụ: ca `Tik2`), thay thế slot ca đó bằng một tài khoản dự phòng có sẵn mật khẩu chuẩn.
     * Cập nhật đồng bộ thông tin tài khoản mới vào file cấu hình ca tương ứng (`Tik2.xlsx`) và cập nhật tracking workbook.
  3. Đảm bảo 7/8 hoặc 8/8 tài khoản trên máy đều ở trạng thái hoạt động sạch trước khi bàn giao máy về hàng đợi tự động.

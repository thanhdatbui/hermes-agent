# TikTok Reg & Gmail Live Check Reference (2026-08-21)

## 1. Quy tắc Lưu Password TikTok (Khi không qua màn đặt pass)
- Khi reg TikTok bằng email (Gmail/Hotmail) đi theo flow OTP hoặc email-only mà TikTok **không hiển thị màn hình tạo mật khẩu**:
  - BẮT BUỘC để trống cột **PASS** (`None` / rỗng) trong file `taikhoan_dat_v2_updated .xlsx`.
  - **CẤM** tạo và lưu mật khẩu ngẫu nhiên vào file Excel, vì cần để trống để người vận hành/tool sau này vào cài pass sau.
- Chỉ lưu mật khẩu khi thực tế có qua màn hình nhập/tạo password và nhập thành công trên app.

## 2. Quy tắc Giữ Lock & Nhả Lock trong Batch Reg
- **Máy thành công (`VERIFIED_SUCCESS`):** Tự động dọn dẹp app về Home và giải phóng device lock (`lease.release()`).
- **Máy thất bại / lỗi (`FINAL_BLOCKED`):** BẮT BUỘC giữ nguyên hiện trường trên thiết bị, giữ device lock ở trạng thái `blocked` (không được tự ý unlock hàng loạt).
- **Báo cáo máy lỗi:** Chụp ảnh screencap, vẽ banner đỏ trên đầu ảnh định dạng `[MAY XX] - HH:MM DD/MM`, gửi ảnh thật (`MEDIA:<path>`) kèm giải thích tiếng Việt cực ngắn gọn.

## 3. Quy trình Kiểm tra Mail Live khi không nhận được OTP TikTok
Khi đăng ký TikTok bằng Gmail mà hộp thư không nhận được OTP mới (hoặc chỉ có OTP cũ từ nhiều ngày trước):
1. **Truy cập trang Quản lý Tài khoản Google:**
   - Mở app Gmail -> Tap Avatar -> Chọn *"Quản lý Tài khoản Google của bạn"*.
2. **Kiểm tra trạng thái phiên qua ATX XML (CẤM tap mù):**
   - Nếu vào thẳng các tab (`Bảo mật`, `Thông tin cá nhân`...) -> Tài khoản **LIVE**.
   - Nếu hiển thị *"Hoàn tất đăng nhập để tiếp tục / Đã xảy ra lỗi và bạn cần đăng nhập lại"*:
     - Dùng ATX XML xác định tọa độ node nút **"Đăng nhập"** (xanh) -> Tap.
     - Dùng ATX XML xác định tọa độ node nút **"TIẾP THEO"** -> Tap.
3. **Phân loại Mail Chết (Google reCAPTCHA Gate):**
   - Nếu màn hình xuất hiện *"Xác nhận bạn không phải là rô-bốt / reCAPTCHA: Tôi không phải là người máy"* (`GoogleLiveState.CAPTCHA`):
     - Xác định đây là **Mail Chết / Bị khóa xác minh robot**.
     - Kích hoạt module `cleanup_blocked_captcha_account` (trong repo `D:\Taadaa\add mail khoi phuc\run_add_recovery.py`):
       1. Xóa tài khoản Google khỏi thiết bị Android (`remove_from_device`).
       2. Xóa dòng tài khoản khỏi file nguồn `gmail_clean_v2.xlsx` (có backup).
       3. Dọn dẹp dòng trống trong tracking `taikhoan_dat_v2_updated .xlsx`.
       4. Đóng app về Home và nhả lock thiết bị.

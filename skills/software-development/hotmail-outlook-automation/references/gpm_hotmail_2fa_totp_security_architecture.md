# Quy Trình Chuẩn Bật 2FA TOTP Hotmail & Cơ Chế Chống Back Tài Khoản (2026-10-09)

## 1. Cơ Chế Bảo Mật Của Microsoft (Findings Thực Nghiệm 100%)
- **Thêm Authenticator vs Bật Two-Step Verification:**
  - Chỉ thêm Authenticator App vào danh sách proof thì công tắc tổng Two-step verification vẫn ở trạng thái TẮT (`OFF`). Khi đó, Microsoft vẫn ưu tiên hỏi mã qua Mail khôi phục khi login/reset.
  - **Bắt buộc kích hoạt công tắc tổng:** Điều hướng `https://account.live.com/proofs/EnableTfa`, bấm qua các màn hình hướng dẫn ("Tiếp theo" -> "Tiếp theo" -> "Hoàn tất") để chuyển Two-step verification sang `ON`.
- **Cơ chế chống Back Account (Bên bán cũ có Mail khôi phục cũng bất lực):**
  - Khi 2FA đã BẬT, Microsoft khóa vĩnh viễn form khôi phục tài khoản thông thường (ACSR).
  - Khi bên bán bấm "Quên mật khẩu / Reset Password", Microsoft bắt buộc phải vượt qua 2 yếu tố độc lập:
    * Yếu tố 1: Nhập OTP từ Mail khôi phục.
    * Yếu tố 2: **Phương thức Email bị khóa xám ("Đã được sử dụng")**. Bắt buộc phải nhập mã 6 số từ Authenticator App (hoặc mã 25 ký tự phục hồi).
    * Nếu không có 2FA: Microsoft treo phong tỏa thay đổi thông tin 30 ngày. Bên bán hoàn toàn không thể đổi pass chiếm lại tài khoản.
- **Đăng nhập hàng ngày khi mất Mail khôi phục:**
  - Đăng nhập thông thường chỉ yêu cầu: **Email + Mật khẩu + Mã 2FA TOTP (6 số)**.
  - Microsoft **không bao giờ hỏi đến Mail khôi phục** khi login thường. Server mail domain (`fviainboxes.com`) có sập thì tài khoản vẫn hoạt động bình thường trên GPM / Farm.

## 2. Tiêu Chuẩn Ảnh Bằng Chứng Thị Giác (Tránh Bị Chê "Chụp Như Cặc")
- **Không crop quá sát:** Crop sát chỉ vài dòng chữ sẽ làm mất context, méo tỷ lệ, lẹm viền nút bấm và chữ.
- **Tiêu chuẩn chụp form đăng nhập / dialog:**
  - Giữ nguyên ảnh full-page 1280x720 hoặc crop bao trọn toàn bộ khung trắng của Form (khoảng `y=80:640, x=420:860` trên viewport 1280x720) để thấy đầy đủ logo Microsoft, email, tiêu đề, input, và các nút điều hướng.
- **Checkpoint bắt buộc gửi MEDIA:**
  1. Checkpoint Pre-Password: Điền xong email & pass trước khi submit.
  2. Checkpoint Pre-TOTP: Hiển thị form 2FA kèm mã 6 số đã điền vào ô input.
  3. Checkpoint Post-TOTP: Màn hình KMSI ("Duy trì đăng nhập?").
  4. Checkpoint Post-Login: Trang Profile Microsoft account với avatar và tên hiển thị.

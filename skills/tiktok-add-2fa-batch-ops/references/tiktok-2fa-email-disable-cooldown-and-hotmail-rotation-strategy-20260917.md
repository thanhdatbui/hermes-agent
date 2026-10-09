# Chiến Lược 2FA TikTok & Đổi Pass Hotmail Chống Back Tài Khoản (17/09/2026)

## 1. Bản Chất Nghiệp Vụ: Bỏ Bước Ép Tắt Xác Thực Qua Email Trên TikTok
- **Thực trạng kỹ thuật:**
  - Trên các phiên bản TikTok mới (v46+), với các tài khoản **chưa từng liên kết Số điện thoại (no-phone)**:
    - Khi script cố gắng bấm `Xóa Email` và bấm `Xác nhận` trong bảng Xác minh 2 bước, server TikTok lập tức ném lỗi Toast:
      > ⛔ **"Không thể thay đổi cài đặt vì lý do bảo mật, hãy thử lại sau"** *(Ảnh bằng chứng: `D:\Taadaa\m30_toast_xoa.png`)*
    - Server TikTok tự động giữ nguyên trạng thái `Email: Bật` như một cơ chế Security Cooldown và kênh khôi phục dự phòng bắt buộc khi không có SĐT.
    - Script Phase B kiểm tra `_wait_stable(lambda xml: _method_checked(xml, "Email") is False)` sẽ bị treo và ném ngoại lệ `EMAIL_DISABLE_NOT_STABLE`.
- **Chỉ đạo dứt khoát từ Operator (17/09/2026):**
  - **KHÔNG CẦN CỐ TẮT 2FA EMAIL NỮA**:
    1. Cố gỡ chỉ làm runner fail vô ích và tốn iterations xử lý UI.
    2. Mục đích ban đầu của việc tắt 2FA email là sợ bên bán Hotmail back tài khoản qua OTP mail.
    3. Nhưng khi xuất xưởng / giao tài khoản cho khách, bắt buộc phải giao trọn gói cả Hotmail đi kèm (nghĩa là nếu có gỡ ra thì sau này khách cũng phải mất công thêm mail vào lại).

---

## 2. Dịch Chuyển Trọng Tâm Phòng Thủ: Đổi Pass Hotmail Sớm
- **Giải pháp triệt để:** Thay vì mất thời gian ép TikTok tắt email, **đổi mật khẩu Hotmail và gỡ sạch mail khôi phục của bên bán ngay từ đầu**:
  - Bên bán Hotmail mất hoàn toàn quyền truy cập hộp thư $\rightarrow$ Không thể lấy OTP hay bấm Magic Link để back tài khoản TikTok.
  - Sau khi đổi pass Hotmail: Thực hiện cấp lại `refresh_token` Microsoft Graph API tự động bằng Chrome trên máy S7 (xem skill `hotmail-outlook-automation` - `references/hotmail-password-rotation-and-oauth-token-regeneration.md`).
- **DoD Chuẩn Của Flow Add 2FA TikTok:**
  - `Trình xác thực (TOTP)`: Bật (Secret 32 ký tự ghi vào cột E Excel).
  - `Mật khẩu TikTok`: Bật (Đổi sang mật khẩu mạnh ngẫu nhiên ghi vào cột D Excel).
  - `Lưu thông tin đăng nhập`: Bật.
  - `Email`: Giữ nguyên `Bật` (bỏ qua bước bấm xóa để runner kết thúc nhanh và thành công 100%).

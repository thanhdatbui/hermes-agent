# Quy tắc Tối cao về Hotmail Khoalee, Không Add Mail Khôi phục & Luồng Thay Mail TikTok

*Thời điểm chốt chỉ đạo:* 18/09/2026

## 1. Hotmail dính líu tới Khoalee — TUYỆT ĐỐI KHÔNG ĐỔI MẬT KHẨU
- **Nhận diện:** Danh sách 50 tài khoản Hotmail/TikTok có email khôi phục gốc là `khoaleemagic@gmail.com` hoặc `khoalemagic@gmail.com` (đối soát trực tiếp từ `D:\OneDrive\codex_gmail_debug\register gmail\gmail_clean_v2.xlsx`).
- **Nguyên tắc:** **TUYỆT ĐỐI BỎ QUA (SKIP 100%)** khi chạy script đổi mật khẩu Hotmail `change_info_hotmail.py` hay cron đêm `night-hotmail-security-watchdog`.
- **Lý do kỹ thuật:** Khi đăng nhập vào web Microsoft, các tài khoản này sẽ bị chặn ở màn hình xác minh danh tính và bắt mã OTP gửi về hộp thư `khoaleemagic@gmail.com`. Không thể tự động hóa và không được làm phiền anh Khoa để xin OTP.

## 2. Kỷ luật Bảo mật Cá nhân — CẤM THÊM MAIL KHÔI PHỤC CỦA OPERATOR
- **Nguyên tắc Clean Delivery:** Tài khoản Hotmail sau này sẽ được xuất xưởng bán kèm trọn gói với tài khoản TikTok cho khách hàng. Mọi tài khoản Hotmail phải giữ sạch 100% ở định dạng `USER | PASS`.
- **CẤM TUYỆT ĐỐI:** Không bao giờ được điền email cá nhân của Operator (ví dụ `thanhdatbui...`) vào mục email khôi phục của Hotmail.
- **Xử lý khi bị ép thêm mail khôi phục:** Nếu trang web Microsoft bắt buộc phải add thêm email khôi phục mới thì mới cho đổi mật khẩu hoặc gỡ mail cũ của bên bán -> **DỪNG LẬP TỨC (ABORT)**, chụp ảnh màn hình hiện trường và gửi báo cáo lại cho Operator, tuyệt đối không tự ý xử lý.

## 3. Luồng Thay Mail TikTok cho Acc Khoalee & Gmail DIE: "Add 2FA Trước -> Thay Mail Sau"
- **Nguyên tắc cốt lõi:**
  1. **Add 2FA TikTok TRƯỚC:** Tài khoản TikTok bắt buộc phải được bật Trình xác thực TOTP 2FA (Secret Key 32 ký tự tại Cột E) và có Mật khẩu TikTok mạnh (Cột D) trước.
  2. **Thay Mail TikTok SAU:** Sau khi đã có 2FA TOTP, nick được bảo vệ kép. Lúc này, TikTok cho phép bấm *Thay đổi email* mà không cần OTP từ email cũ (hoặc chỉ cần nhập mã TOTP 2FA hiện tại để xác minh danh tính).
- **Quy trình thay mail tự động:**
  - Kiểm tra điều kiện: Nick thuộc 50 acc dính khoalee HOẶC có Gmail liên kết bị DIE (kiểm tra qua `check_gmail_live_fast.py`).
  - Mua 1 Hotmail mới qua API `buy_hotmail.py` (BoxTaiKhoan/CloneFBIG) lấy `email|pass|refresh_token|client_id`.
  - Mở TikTok -> Cài đặt -> Tài khoản -> Thông tin tài khoản -> Email -> Thay đổi email.
  - Vượt gate xác minh danh tính bằng mã 2FA TOTP (sinh từ Secret Key Cột E).
  - Điền Hotmail mới -> Polling Microsoft Graph API đọc OTP 6 số -> Nhập vào TikTok xác nhận.
  - Cập nhật Cột F (Email mới) và Cột G (Pass Hotmail) trong Excel.
  - Đăng nhập Hotmail trên Chrome của máy S7 để bắt đầu tính chu kỳ ngâm 7 ngày.

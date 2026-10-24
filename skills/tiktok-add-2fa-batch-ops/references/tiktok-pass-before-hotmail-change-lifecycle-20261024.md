# Thứ Tự Vòng Đời Bắt Buộc: Tạo Pass TikTok Trước, Đổi Pass Hotmail Sau (24/10/2026)

## 1. Bản chất sự cố và phát hiện vận hành
- **Hiện tượng**:
  * Tại cụm Admin (M201-280), có 270 tài khoản TikTok (trong đó 229 tài khoản đang ở trạng thái `WAIT_7D`) có Cột 3 `ID` (username TikTok) nhưng Cột 4 `PASS` TikTok lại để trống (`None`).
  * Supervisor GPM (`batch_gpm_5profiles_supervisor.py`) và Báo cáo 6H chặn không cho chuyển sang `CHANGE_INFO` đổi mật khẩu Hotmail vì điều kiện:
    `has_tiktok = bool(username and password)` đánh giá là `False`.
- **Nguyên nhân để trống Pass TikTok**:
  * Khi đăng ký TikTok bằng Hotmail theo luồng Email-only / OTP trên điện thoại (`tiktok-reg-hotmail-outlook-flow`), TikTok chuyển thẳng từ xác thực OTP sang ngày sinh và vào profile mà **không hề qua màn đặt mật khẩu**.
  * Farm có kỷ luật nghiêm ngặt: *CẤM ghi mật khẩu giả khi không có màn nhập password*. Do đó Cột PASS được để trống đúng thực tế.

---

## 2. Invariant Thứ Tự: "Xử Lý Tạo Pass + 2FA TikTok Xong Thì Hotmail Mới Được Đổi"
- **NGHIÊM CẤM NỚI LỎNG GUARD**:
  * Tuyệt đối **CẤM** sửa điều kiện supervisor từ `bool(username and password)` thành `bool(username)` để cưỡng ép đổi mật khẩu Hotmail cho nick thiếu pass TikTok.
- **RỦI RO CHÍ MẠNG KỸ THUẬT NẾU ĐỔI PASS HOTMAIL TRƯỚC**:
  1. Khi nick TikTok chưa có mật khẩu, bước vào cài đặt bảo mật để tạo mật khẩu mới (`ensure_account_password_saved` trong `live_phase_b_adapter.py`) sẽ kích hoạt màn hình **Xác minh danh tính (Verify your identity)**.
  2. TikTok bắt buộc **gửi mã OTP 6 số về hòm thư Hotmail liên kết**.
  3. Để script trên điện thoại đọc được mã OTP này (qua Outlook app hoặc PC Graph API), **hòm thư Hotmail bắt buộc phải đang hoạt động bình thường với mật khẩu hiện tại**.
  4. Nếu đổi mật khẩu Hotmail trên GPM trước (hoặc bật 2FA Microsoft trước), tài khoản Hotmail trên điện thoại bị văng session hoặc không đăng nhập được:
     ➔ Không đọc được OTP xác minh danh tính của TikTok.
     ➔ Nick TikTok bị kẹt vĩnh viễn không thể tạo mật khẩu hay bật 2FA TikTok.

---

## 3. Quy trình thực thi chuẩn hóa 2 giai đoạn (Standard 2-Phase Protocol)
1. **Giai đoạn 1: Tạo Pass TikTok + Bật 2FA TikTok trên thiết bị**:
   - Chạy batch `tiktok-add-bao-mat-f2a` (`run_batch_live_2fa.py` / `run_capture_phase_b.py`).
   - Hàm `password_needs_rotation(pwd_val)` nhận diện ô Password rỗng (`None`) ➔ Tự động kích hoạt luồng:
     * Nhận OTP từ Hotmail cũ còn sống.
     * Điền OTP vào TikTok mở khóa màn hình *Tạo mật khẩu*.
     * Sinh mật khẩu mạnh 18 ký tự (`generate_account_password()`) và điền vào form.
     * Lưu mật khẩu mới vào Cột 4 (`PASS`) và 2FA Secret vào Cột 5 (`2FA`) của file Excel.
2. **Giai đoạn 2: Đổi Pass Hotmail + Bật 2FA Microsoft trên GPM**:
   - Sau khi Giai đoạn 1 hoàn tất, Cột 4 Excel đã có mật khẩu TikTok hợp lệ.
   - Supervisor kiểm tra thấy `has_tiktok = bool(username and password)` đã đạt `True`.
   - Supervisor mới tự động cấp quota cho tài khoản chuyển từ `WAIT_7D` sang `CHANGE_INFO` để chạy `gpm_change_hotmail_security.py` đổi mật khẩu Hotmail và bật 2FA Microsoft an toàn.

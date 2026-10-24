# Silent Fail-Safe Khi Tạo Pass TikTok & Rào Chắn Bất Biến Dual Credential Hotmail (24/10/2026)

## 1. Rào Chắn Bất Biến (Invariant): Hotmail Chỉ Được Đổi Khi Đã Có Đủ ID + PASS TikTok
- **Nguyên tắc sống còn của Farm:**
  * Nick TikTok chỉ thực sự hoàn thiện khi có đầy đủ cả **Username (Cột 3)** và **Mật khẩu TikTok (Cột 4)** trong workbook tracking (`taikhoan_dat_v2_updated .xlsx`).
  * Chỉ khi tài khoản TikTok đã có cả ID và PASS thì Supervisor GPM mới được cấp phép chuyển nick từ `WAIT_7D` sang `CHANGE_INFO` để đổi mật khẩu và bật 2FA Hotmail.
  * **CẤM TUYỆT ĐỐI** hạ rào chắn `has_tiktok = bool(username and password)` thành `bool(username)` vì lý do "nick đã có ID và đang chạy video". Nếu đổi pass Hotmail trước khi TikTok có mật khẩu, TikTok sẽ không thể gửi OTP xác minh tạo pass về hòm thư điện thoại được nữa -> Nick bị kẹt vĩnh viễn không đặt được pass.

## 2. Bản Chất Sự Cố: 2FA Bật Thành Công Nhưng Mật Khẩu Vẫn Là `None`
- **Hiện tượng thực tế kiểm tra (24/10/2026):**
  * Trên cụm Admin (630 nick): có 34 nick đã bật 2FA (có mã Secret 32 ký tự ở Cột 5).
  * Nhưng trong 34 nick đó: **33 nick Cột 4 PASS vẫn hoàn toàn là `None`** (chỉ có 1 nick có pass cũ).
  * Trên cụm Kibe: runner tạo thành công mật khẩu dạng `<chars>-<digits>-<dash>` (18 ký tự) cho 19 nick, nhưng vẫn còn 40 nick trống pass.
- **Nguyên nhân kỹ thuật — Cạm bẫy Silent Fail-safe trong `live_phase_b_adapter.py`:**
  * Trong `execute_phase_b()`, thứ tự thực hiện là:
    1. Thiết lập Authenticator App (2FA) -> Lưu mã 2FA Secret vào workbook.
    2. Tắt phương thức Email.
    3. Gọi `operations.ensure_password_saved()` -> kích hoạt `adapter.ensure_account_password_saved()`.
  * Tại `ensure_account_password_saved()` (khoảng dòng 902–905):
    ```python
    # Fail-safe: Nếu sau 8 lần điều hướng không vào được form đổi mật khẩu (do TikTok
    # đổi nhánh UI / yêu cầu OTP email không có method password), giữ nguyên mật khẩu
    # hiện tại trong workbook, không ném ngoại lệ làm crash toàn bộ phiên add 2FA đã thành công.
    return
    ```
  * Khi runner gọi `_read_device_email_otp()` để lấy OTP qua app Outlook trên máy S7, nếu Outlook chưa đăng nhập sẵn phiên của nick đó hoặc dính popup chặn, helper trả về `None` -> runner thoát hàm trong im lặng.
  * Phiên được báo cáo là `SUCCESS`, mã 2FA Secret đã nằm trong Excel, nhưng **Mật khẩu mới chưa hề được tạo và Cột 4 vẫn là `None`**.

## 3. Quy Trình Vận Hành & Khắc Phục Chuẩn
1. **Kiểm tra tách bạch 2FA và Mật khẩu (Không nhìn mỗi cột 2FA):**
   * Khi đánh giá tiến độ add 2FA, bắt buộc đếm đồng thời:
     - `has_2fa`: số nick có mã 2FA Secret ở Cột 5.
     - `has_pass`: số nick có mật khẩu ở Cột 4.
     - `has_both`: số nick có cả 2FA và PASS.
   * Runner gom target theo ưu tiên:
     `candidates.sort(key=lambda item: (not item.blank_pass, item.password_only, not item.has_journal, item.source_row))`
     Ưu tiên hàng đầu (`blank_pass=True`) là các nick đang thiếu pass.
2. **Xử lý trước khi cho phép Hotmail đổi pass:**
   * Các nick có 2FA nhưng thiếu pass (`pw_only = has_2fa and needs_pwd`) phải được chạy tiếp với cờ `--password-only` hoặc qua runner Phase B để hoàn tất bước tạo mật khẩu TikTok.
   * Chỉ khi Cột 4 trong Excel được điền mật khẩu thật sự, vòng đời Hotmail trên GPM mới tự động mở khóa chuyển sang `CHANGE_INFO`.

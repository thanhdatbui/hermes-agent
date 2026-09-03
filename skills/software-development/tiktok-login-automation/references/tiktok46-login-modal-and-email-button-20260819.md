# TikTok 46.x Login Sheet, Bottom-Sheet Switcher & Email Icon Button (2026-08-19)

## 1. Màn hình Auth Bottom-Sheet (`I18nSignUpActivity`) khi máy chưa có tài khoản
- Khi thiết bị ở trạng thái đăng xuất hoàn toàn (chưa có tài khoản nào), mở app TikTok hoặc tap tab **Hồ sơ** sẽ bung modal/bottom-sheet `I18nSignUpActivity`.
- **Dấu hiệu nhận diện:** XML chứa `dang nhap` + `tiep tuc voi email/ten nguoi dung` + `so dien thoai` + `tao tai khoan`.
- **Cạm bẫy:**
  - Script cũ tìm `dang ky tiktok` + `ban da co tai khoan? dang nhap` -> bị trượt nhận diện `is_auth_landing_screen`.
  - Cố gọi `open_account_dropdown` / `tap_add_account` trên màn hình này sẽ fail `[03_dropdown] Khong mo duoc account dropdown` vì máy chưa có tài khoản nào để mở switcher.
- **Xử lý chuẩn:**
  - `is_auth_landing_screen`: chấp nhận cả `dang nhap` + `tiep tuc voi email`.
  - `ensure_login_entry_screen`: kiểm tra `is_auth_landing_screen` cả trước và sau khi tap tab profile; nếu đã ở auth landing thì bypass qua bước chọn phương thức email (`choose_email_login`).

## 2. Bug nút "Tiếp tục" / "Đăng nhập" khớp nhầm đoạn Text Điều khoản pháp lý
- Dưới chân màn hình đăng nhập có đoạn text pháp lý dài: *"Bằng việc tiếp tục với tài khoản có vị trí tại Việt Nam, bạn đồng ý với Điều khoản Dịch vụ..."*
- Vì đoạn text này chứa chữ *"tiếp tục"*, hàm `find_node_in_xml` / `node_has_target` nếu match substring lỏng lẻo sẽ click nhầm vào tọa độ chân trang `(540, 1794)` -> mở Webview Điều khoản dịch vụ thay vì submit đăng nhập.
- **Fix:** Trong `find_node_in_xml`, lọc và ưu tiên **Exact match** (`exact_matches`) cho các target ngắn (`Đăng nhập`, `Tiếp tục`, `Log in`) trước khi xét partial match; đồng thời giới hạn chiều dài chuỗi node text `<= 50` ký tự cho partial match. Tọa độ chuẩn của nút **ĐĂNG NHẬP** màu đen là `(540, 878)`.

## 3. Nút tròn Icon Email `(233, 1693)` khi thêm tài khoản thứ 2, 3...
- Khi đã có tài khoản trên máy, vào Profile -> tap header mở *Chuyển đổi tài khoản* -> tap *Thêm tài khoản* -> TikTok mở form đăng nhập mặc định ở tab **Số điện thoại** (`VN +84`).
- Không có tab text "Email/Tên người dùng" nằm ngang ở trên như bản cũ.
- Tùy chọn chuyển sang Email nằm ở **nút tròn màu trắng có icon phong bì thư ✉️** ở góc dưới bên trái:
  - Bounds XML: `[161, 1621][305, 1765]` (node `android.view.View`, không có text/desc).
  - Tọa độ tap tâm chuẩn: **`(233, 1693)`**.
- Sau khi tap nút này, form chuyển sang EditText nhập Email `[138, 566][942, 626]`.

## 4. Xử lý Chuyển đổi giữa OTP và Mật khẩu / 2FA TOTP
- Sau khi nhập email:
  - Nếu TikTok nhảy vào màn hình OTP nhưng có link *"Đăng nhập bằng mật khẩu"* (`[96, 1119][703, 1236]` -> `(400, 1177)`): Tap vào link này để chuyển sang nhập password trực tiếp.
  - Nếu yêu cầu mật khẩu: Điền password qua Base64 Broadcast của `com.github.uiautomator/.AdbKeyboard` -> tap nút Tiếp tục `(540, 933)`.
  - Nếu yêu cầu 2FA Authenticator (TOTP): Đọc secret base32 từ cột `2FA` của workbook -> sinh mã 6 số qua `pyotp.TOTP(secret).now()` -> điền và submit.
  - Sau login: Tự động dismiss popup Danh bạ (tap *TỪ CHỐI* `(557, 1134)`).

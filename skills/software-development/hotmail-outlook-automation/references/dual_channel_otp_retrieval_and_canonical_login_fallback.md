# Hotmail Dual-Channel OTP: Graph API vs Canonical Webmail Login

## Nguyên tắc chỉ đạo từ thực tế vận hành
1. **Graph API chỉ áp dụng cho Hotmail còn token:**
   - Các tài khoản mua có kèm `refresh_token` và `client_id` còn hiệu lực.
   - Gọi Microsoft Graph API lấy OTP $O(1)$ tức thì, không cần tải giao diện browser.
   - Khi token hết hạn hoặc lỗi `400 / invalid_grant`, Graph API sẽ thất bại.

2. **Hotmail không còn token bắt buộc phải vào hòm thư đọc qua giao diện Web:**
   - Dành cho tài khoản mua dạng `mail|pass` thuần túy hoặc tài khoản bị revoke token.
   - **Kỷ luật cốt lõi:** Tuyệt đối KHÔNG tự viết script login mới / ad-hoc.
   - BẮT BUỘC sử dụng lại đúng các hàm và selector chuẩn từ các luồng đăng nhập Hotmail/GPM đã kiểm chứng trong repo (`D:/Taadaa/Hotmail/scripts/batch_gpm_hotmail_password_login.py` và `read_otp_gpm.py`):
     * Email field: `#i0116` / `input[name="loginfmt"]`
     * Chuyển phương thức sang mật khẩu: bắt và click nút `#idA_PWD_SwitchToPassword` ("Sử dụng mật khẩu của bạn / Use your password instead")
     * Password field: `#i0118` / `input[name="passwd"]`
     * Submit button: `#idSIButton9` / `input[type="submit"]`
     * Bỏ qua duy trì đăng nhập (KMSI): `#idSIButton9` hoặc `#declineButton`
     * Đọc thư: Quét các hàng email (`[role="row"]` hoặc nội dung trang hòm thư đến) bóc mã OTP 6 số.

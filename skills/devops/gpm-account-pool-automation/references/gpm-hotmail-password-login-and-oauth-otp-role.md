# GPM Hotmail Password Login & OAuth Token Auxiliary Role

## 1. Rule & Core Interpretation
- **Định dạng tài khoản Hotmail mua**: `email|password|refresh_token|client_id`.
- **Vai trò thực tế**:
  - `email` + `password`: Dùng để đăng nhập giao diện web trình duyệt (`https://login.live.com`) trên GPMLogin.
  - `refresh_token` + `client_id`: **Không phải** để inject OAuth session vào browser. Token này chỉ mang tính chất **hỗ trợ (auxiliary)** nhằm lấy `access_token` và đọc OTP / security verification code từ hòm thư qua Microsoft Graph API (`https://graph.microsoft.com/v1.0/me/messages`) khi Microsoft yêu cầu xác minh danh tính.
- **Cấm kỵ (Hard Rule)**:
  - Tuyệt đối **không chặn (BLOCKED)** batch chỉ vì không có script "Microsoft OAuth browser-session injector".
  - Luôn thực hiện form login `login.live.com` bằng email/password trước.

## 2. Profile Creation & Naming Standard
- **Format tên profile**: `<machine 2-digit> - <email> - <proxy-port>` (Ví dụ: `02 - vjorandrea1961@hotmail.com - 5102`).
- **Proxy**: Gán `raw_proxy` trực tiếp khi tạo profile (`client.create_profile(name=..., raw_proxy=..., group_id=1, browser_type="Chrome")`).
- **Khởi động profile**: Dùng `skip_proxy_check=True` để tránh GPM API treo do internal proxy ping timeout.

## 3. Automation Flow qua Playwright CDP
1. **Kiểm tra Egress IP**: Điều hướng tới `https://api.ipify.org?format=json` để kiểm tra IP ra của proxy trước khi login.
2. **Login live.com**:
   - Điền email vào `#i0116` / `input[name="loginfmt"]`.
   - Nếu xuất hiện lựa chọn "Sử dụng mật khẩu của bạn" / "Use your password instead" (`#idA_PWD_SwitchToPassword`), click chuyển sang nhập mật khẩu.
   - Điền password vào `#i0118` / `input[name="passwd"]`.
3. **Xử lý màn hình phụ (Interstitial Screens)**:
   - **KMSI ("Duy trì đăng nhập?" / "Stay signed in?")**: Click "Có" / "Yes" (`#idSIButton9`) để lưu phiên đăng nhập bền vững.
   - **Terms update ("Chúng tôi đang cập nhật các điều khoản")**: Click Next / Tiếp tục (`#iNext` hoặc `#idSIButton9`).
   - **Authenticator Promo ("Break free from your passwords")**: Click "Không, cảm ơn" / "No thanks" / "Bỏ qua" (`#iCancel`).
4. **Xử lý Challenge / OTP**:
   - Nếu Microsoft yêu cầu OTP gửi về hòm thư: Dùng `refresh_token` + `client_id` gọi `https://login.microsoftonline.com/common/oauth2/v2.0/token` lấy `access_token`, rồi đọc message từ `https://graph.microsoft.com/v1.0/me/messages` để lấy mã 6 số.
   - Nếu gặp challenge không thể tự động xử lý (SMS qua số lạ, Authenticator app prompt của bên thứ ba, Captcha, hoặc Account Locked): Chụp ảnh màn hình, lưu bằng chứng và dừng tài khoản đó với trạng thái `BLOCKED`, tiếp tục xử lý các tài khoản còn lại trong batch.
5. **Dọn dẹp**: Luôn đóng profile trong khối `finally` (`client.stop_profile(profile_id)`).

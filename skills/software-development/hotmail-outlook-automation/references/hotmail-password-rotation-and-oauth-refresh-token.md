# Đổi Mật Khẩu Hotmail Sớm Chống Back & Tự Động Sinh Token OAuth2 Microsoft

## 1. Bản Chất Nghiệp Vụ & Quyết Định Chiến Lược
- **Vấn đề rủi ro:** Tài khoản Hotmail mua từ bên thứ ba dùng để liên kết nuôi nick TikTok nếu không đổi mật khẩu sớm thì bên bán hoàn toàn có thể dùng mật khẩu gốc/mail khôi phục cũ để back (chiếm đoạt) tài khoản sau khi nick đã lên tương tác.
- **Bẫy kỹ thuật OAuth2:** Đổi mật khẩu Microsoft/Hotmail làm **revoke (hủy hiệu lực)** toàn bộ `refresh_token` cũ của shop cung cấp, dẫn đến việc các công cụ đọc mã OTP qua Graph API (`scripts/test_graph_token.py`) bị từ chối `400 Bad Request` / `invalid_grant`.
- **Giải pháp dứt khoát:**
  1. Đổi mật khẩu Hotmail và gỡ sạch thông tin khôi phục cũ của bên bán ngay trên thiết bị S7 qua proxy của máy để chống checkpoint/IP lạ.
  2. Không cần tắt phương thức xác thực qua Email trên TikTok (tránh dính lỗi `EMAIL_DISABLE_NOT_STABLE` do Security Cooldown của TikTok trên tài khoản no-phone; và sau này giao acc cho khách vẫn cần bàn giao full mail).
  3. Kích hoạt flow OAuth2 trên trình duyệt thiết bị để cấp lại `refresh_token` mới và cập nhật thẳng vào file dữ liệu của farm.

## 2. Quy Trình Cấp Lại `refresh_token` Microsoft Mới Qua Trình Duyệt Thiết Bị
- **Endpoint Authorize chuẩn:**
  ```text
  https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=9e5f94bc-e8a4-4e73-b8be-63364c29d753&response_type=code&redirect_uri=https://login.microsoftonline.com/common/oauth2/nativeclient&scope=https://graph.microsoft.com/Mail.Read%20offline_access&prompt=login&login_hint=<EMAIL>
  ```
- **PITFALL CỰC KỲ NGUY HIỂM (ADB Shell URL truncation):**
  - Khi mở URL bằng lệnh `am start -a android.intent.action.VIEW -d "<URL>"` qua ADB shell, các ký tự `&` trong URL **BẮT BUỘC phải được escape dạng `\&`** hoặc bọc trong danh sách tham số chuẩn (tránh shell Linux/Android ngắt lệnh chạy nền làm cụt URL).
  - Triệu chứng nếu thiếu escape: Microsoft hiển thị lỗi:
    `AADSTS900144: The request body must contain the following parameter: 'scope'.`
- **Các bước tương tác:**
  1. Nếu có ô nhập mật khẩu: điền mật khẩu mới và submit (`idSIButton9`).
  2. Màn hình KMSI ("Duy trì đăng nhập / Stay signed in?"): Bấm Yes (`idSIButton9`).
  3. Màn hình Consent ("Cho phép ứng dụng này..."): Bấm Chấp nhận (`idBtn_Accept`).
  4. Bắt URL redirect tại Chrome `https://login.microsoftonline.com/common/oauth2/nativeclient?code=M.C...`.
  5. Đổi `code` lấy `refresh_token` mới:
     ```python
     POST https://login.microsoftonline.com/common/oauth2/v2.0/token
     data = {
         "client_id": "9e5f94bc-e8a4-4e73-b8be-63364c29d753",
         "grant_type": "authorization_code",
         "code": code,
         "redirect_uri": "https://login.microsoftonline.com/common/oauth2/nativeclient",
         "scope": "https://graph.microsoft.com/Mail.Read offline_access",
     }
     ```
  6. Verify đọc thư mục tin nhắn qua Microsoft Graph API:
     `GET https://graph.microsoft.com/v1.0/me/messages` với header `Authorization: Bearer <access_token>`.

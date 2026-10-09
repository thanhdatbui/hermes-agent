# Flow Lấy Refresh Token Mới Qua Chrome Trên Thiết Bị Android (OAuth2 Native Client)

Khi một tài khoản Hotmail bị hỏng/hết hạn `refresh_token` (hoặc shop cấp token không hợp lệ), có thể thực hiện cấp lại refresh token trực tiếp trên điện thoại Android qua trình duyệt Chrome và Microsoft OAuth2.

## 1. OAuth2 Authorize URL
Mở Chrome trên thiết bị Android bằng intent:
```bash
adb shell am start -a android.intent.action.VIEW -p com.android.chrome -d "<URL>"
```
Trong đó URL có dạng:
```
https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=<CLIENT_ID>&response_type=code&redirect_uri=https://login.microsoftonline.com/common/oauth2/nativeclient&scope=https://graph.microsoft.com/Mail.Read%20offline_access&prompt=login&login_hint=<EMAIL>
```
- `client_id`: Ví dụ `9e5f94bc-e8a4-4e73-b8be-63364c29d753` (hoặc client id của app/shop).
- `redirect_uri`: `https://login.microsoftonline.com/common/oauth2/nativeclient`.
- `scope`: `https://graph.microsoft.com/Mail.Read offline_access`.
- `prompt=login` & `login_hint=<EMAIL>`: Tự động điền email và ép chuyển thẳng đến bước nhập mật khẩu.

## 2. Các Màn Hình UI Cần Xử Lý Trên Chrome
1. **Màn hình Password**:
   - Nhận diện qua input password (resource-id `i0118` hoặc node password trong WebView).
   - Nhập mật khẩu tài khoản qua `type_text` (AdbKeyboard).
   - Bấm nút Đăng nhập / Sign in (`idSIButton9`).
2. **Màn hình KMSI (Keep me signed in / Duy trì đăng nhập)**:
   - Text chứa "Stay signed in?" hoặc "Duy trì đăng nhập?".
   - Bấm nút Có / Yes (`idSIButton9`).
3. **Màn hình Consent (Ủy quyền ứng dụng)**:
   - Xuất hiện khi client_id yêu cầu quyền `Mail.Read` lần đầu ("Cho phép ứng dụng này truy cập...").
   - Bấm nút Cho phép / Chấp nhận / Yes (`idBtn_Accept`).

## 3. Bắt Mã Authorization Code & Đổi Token
- Sau khi xác thực thành công, trình duyệt chuyển hướng về URL:
  `https://login.microsoftonline.com/common/oauth2/nativeclient?code=M.C...`
- Đọc URL từ thanh địa chỉ `url_bar` của Chrome (qua dump XML hoặc tap vào `url_bar` để lấy text).
- Trích xuất giá trị tham số `code=...`.
- Gửi request `POST https://login.microsoftonline.com/common/oauth2/v2.0/token`:
  ```python
  payload = {
      "client_id": client_id,
      "grant_type": "authorization_code",
      "code": code,
      "redirect_uri": "https://login.microsoftonline.com/common/oauth2/nativeclient",
      "scope": "https://graph.microsoft.com/Mail.Read offline_access",
  }
  ```
- Kết quả trả về JSON chứa `refresh_token` mới và `access_token`.

## 4. Xác Thực Token Bằng Graph API
- Sử dụng hàm trong `scripts/test_graph_token.py`:
  Gửi GET request tới `https://graph.microsoft.com/v1.0/me/messages` với header `Authorization: Bearer <access_token>` để kiểm tra đọc hộp thư và bóc tách OTP (TikTok, Microsoft,...).

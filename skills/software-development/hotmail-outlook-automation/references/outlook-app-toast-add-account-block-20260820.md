# Lỗi Toast "Hiện không thể thêm tài khoản này", Sai Mật Khẩu Web & Quy Trình Xử Lý Hotmail Loại 2 (Graph API)

## 1. Hiện tượng & Triệu chứng (Live Verified 2026-08-20, Máy 75, Máy 4, Máy 44)
1. **Trường hợp 1 - Toast chặn email:**
   - **Màn hình:** `com.microsoft.office.outlook.ui.onboarding.login.AddAccountActivity` (Màn hình "Thêm tài khoản" của Outlook app).
   - **Hành động:** Sau khi điền địa chỉ email (VD: `TerraRau76115@hotmail.com`) và nhấn nút "TIẾP TỤC" (`btn_primary_button`) hoặc gửi phím Enter (`keyevent 66`).
   - **Phản hồi từ App:** Xuất hiện Toast màu xám nổi lên:
     > **"Hiện không thể thêm tài khoản này."**
   - **Nguyên nhân:** Proxy bị timeout / chết kết nối ra ngoài internet (như máy 75, 73) hoặc cơ chế chặn từ máy chủ Microsoft.

2. **Trường hợp 2 - Báo sai mật khẩu trên WebView Microsoft:**
   - **Màn hình:** `com.microsoft.office.outlook/com.microsoft.identity.client.internal.MsalUtils` / `AuthorizationActivity` (Màn hình nhập mật khẩu Microsoft).
   - **Hành động:** Nhập mật khẩu được cấp từ shop (hoặc trong workbook) và nhấn "Tiếp theo" / Enter.
   - **Phản hồi từ Microsoft:** Dòng chữ đỏ:
     > **"Mật khẩu đó không đúng với tài khoản Microsoft của bạn."**
   - **Nguyên nhân:** Đối với acc Shop Loại 2 (OAuth2 có token), shop tạo và duy trì session qua OAuth2 client/token, mật khẩu text đi kèm thường không đồng bộ hoặc đã bị vô hiệu hóa cho luồng basic auth / app auth.

## 2. Quy trình kiểm tra & Phân loại xử lý

### A. Đối với Hotmail Loại 2 (Có `refresh_token` + `client_id`)
- **Kiểm tra Token trực tiếp từ PC qua Microsoft Graph Token Endpoint:**
  ```python
  import requests
  url = 'https://login.microsoftonline.com/consumers/oauth2/v2.0/token'
  data = {
      'client_id': client_id,
      'grant_type': 'refresh_token',
      'refresh_token': refresh_token,
      'scope': 'https://graph.microsoft.com/Mail.Read offline_access'
  }
  r = requests.post(url, data=data, timeout=10)
  # r.status_code == 200 -> TOKEN LIVE -> Đọc được /me/messages
  ```
- **Xử lý chuẩn & Đồng bộ TXT ↔ Excel:**
  - Nếu token live (HTTP 200) và đăng nhập app thành công: Nạp trực tiếp vào `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (cột 9 `token`, cột 10 `client_id`) và **XÓA KHỎI file TXT nguồn**.
  - Nếu login lỗi / sai pass: **GIỮ NGUYÊN trong TXT nguồn**, xóa dòng chưa hoàn tất trong Excel.
  - Khi user yêu cầu danh sách lỗi để gửi shop: **CHỈ gửi dạng `email|password`**, KHÔNG gửi token/client_id dài dòng.

### B. Đối với Hotmail Loại 1 (Chỉ có `mail|pass`, không kèm token)
- Nếu bị Toast hoặc sai mật khẩu:
  1. Kiểm tra lại kết nối Proxy bằng cách test curl/requests ra ngoài với proxy format `user:pass@host:port` (URL-encode password nếu có ký tự `#`, `!`).
  2. Nếu Proxy sống mà Microsoft vẫn báo sai mật khẩu: Tuân thủ nghiêm ngặt **STOP GATE**: Chụp ảnh màn hình lỗi, gửi `MEDIA:<path>` cho user, giữ nguyên hiện trường trên máy, dừng chờ user kiểm tra lại pass.

## 3. Quy tắc Device Lock khi chạy Batch
- Khi thực hiện lệnh login batch nhiều máy, bắt buộc phải gọi `automation_core.device_lock.acquire_device_lock` cho toàn bộ các máy trong batch với `user_authorized=True` để giữ độc quyền thiết bị, tránh bị Hermes Cron nuôi acc hoặc các background worker khác tranh chấp màn hình.

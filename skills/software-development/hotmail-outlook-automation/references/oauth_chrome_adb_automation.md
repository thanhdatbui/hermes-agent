# Tự động hóa OAuth2 trên Chrome Android qua ADB (Hotmail / Microsoft Graph)

### 1. Escape dấu `&` trong intent data URL (`-d`)
- **Triệu chứng lỗi**: Microsoft trả về `AADSTS900144: The request body must contain the following parameter: 'scope'`.
- **Nguyên nhân**: Khi thực thi lệnh qua ADB shell:
  `am start -a android.intent.action.VIEW -p com.android.chrome -d <AUTH_URL>`
  Shell của Android (`/system/bin/sh`) hiểu ký tự `&` là toán tử chạy tiến trình nền (background operator), cắt đứt URL ngay tại dấu `&` đầu tiên. Các query parameters phía sau (như `scope`, `prompt`, `login_hint`) bị mất hoàn toàn.
- **Giải pháp**: Luôn escape ký tự `&` trước khi truyền vào lệnh shell ADB:
  ```python
  escaped_url = auth_url.replace("&", r"\&")
  run_adb(adb, serial, "am", "start", "-a", "android.intent.action.VIEW", "-p", "com.android.chrome", "-d", escaped_url)
  ```

### 2. Bẫy Ellipsis (URL Truncation) trên Android Chrome UI Automator
- **Triệu chứng lỗi**: Khi đổi authorization code lấy token qua Microsoft endpoint:
  `400 {"error":"invalid_grant","error_description":"AADSTS9002313: Invalid request. Request is malformed or invalid."}`
- **Nguyên nhân**:
  Khi chuyển hướng đến redirect URI (ví dụ `https://login.microsoftonline.com/common/oauth2/nativeclient?code=...`), thanh địa chỉ Chrome (`com.android.chrome:id/url_bar`) ở trạng thái unfocused sẽ tự động rút gọn và cắt bớt chuỗi text dài bằng dấu chấm lửng (`...`).
  Nếu dùng UI XML dump (`uiautomator dump`) để lấy `url` từ node `url_bar`, regex `code=([a-zA-Z0-9_\-\.]+)` sẽ bắt phải chuỗi code bị cắt ngắn (thường chỉ 20-30 ký tự thay vì độ dài đầy đủ hàng trăm ký tự), khiến grant request bị từ chối do malformed code.
- **Giải pháp**:
  1. **Chrome DevTools Remote Debugging (Khuyến nghị)**:
     Android Chrome lắng nghe trên unix domain socket `localabstract:chrome_devtools_remote`. Chuyển tiếp cổng qua ADB:
     ```bash
     adb forward tcp:9222 localabstract:chrome_devtools_remote
     curl http://localhost:9222/json
     ```
     Đọc trực tiếp field `url` của page target để nhận 100% URL gốc không bị truncate.
  2. **Clipboard Copy**: Tap vào location bar để focus, gửi keyevent chọn tất cả và copy vào clipboard Android, sau đó đọc qua ADB clipboard service hoặc broadcast.

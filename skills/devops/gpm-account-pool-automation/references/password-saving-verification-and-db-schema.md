# Quy Trình Verify Lưu Mật Khẩu GPM Profile & Tra Cứu Database Schema

## 1. GPM Database (`profile_data.db`) Schema
- **Đường dẫn:** `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`
- **Các cột thực tế của bảng `Profiles`:**
  `['Id', 'Name', 'ProfilePath', 'JsonData', 'GroupId', 'CreatedAt', 'S3Path', 'CreatedBy', 'LastRunBy', 'LastRunAt', 'UpdatedAt']`
- **Pitfall:** Không có cột `RawProxy` trực tiếp ở bảng `Profiles`. Proxy được nhúng trong `JsonData`.
- **Query tra cứu profile theo email an toàn:**
  ```sql
  SELECT Id, Name, ProfilePath FROM Profiles WHERE Name LIKE '%<email>%'
  ```
  Nếu không tìm thấy row nào, tức profile chưa được tạo trong GPM -> pipeline sẽ không có `ProfilePath` hợp lệ, cần gọi API v3 tạo profile trước.

## 2. Đường Dẫn Công Cụ & Môi Trường Trên Máy Farm Kibe
- **ADB:** `C:\Program Files (x86)\xiaowei\tools\adb.exe` (không nằm trong system PATH).
- **Chromium Core:** `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe`.

## 3. Quy Trình Kiểm Tra Lưu Mật Khẩu (Post-run Password Saving Verification)
Khi chạy pipeline tự động đăng nhập và lưu mật khẩu vào Chromium profile:
1. **Kiểm tra `Preferences`:**
   - Đọc file JSON `Preferences` (hoặc `Default/Preferences`) trong profile directory.
   - Verify `credentials_enable_service == True` và `profile.password_manager_enabled == True`.
2. **Kiểm tra SQLite `Login Data` / `Login Data For Account`:**
   - Mở database SQLite tại `<profile_path>/Default/Login Data` hoặc `<profile_path>/Login Data`.
   - Query đếm:
     ```sql
     SELECT count(*) FROM logins WHERE origin_url LIKE '%accounts.google.com%'
     ```
   - **Bảo mật:** Tuyệt đối chỉ đếm số lượng bản ghi (`count(*)`), KHÔNG in trường mật khẩu plaintext (`password_value`) ra console/log.
3. **Debug Screenshot Proof:**
   - Liệt kê và kiểm tra screenshot chứng minh trong thư mục `D:\Taadaa\GPM auto\debug_screenshots`.

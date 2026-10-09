# TikTok v46.6.3 Email Login Selector & APK Provisioning Pitfalls (15/09/2026)

## 1. Nút chọn phương thức đăng nhập bằng Email trên TikTok v46.6.3
- **Hiện tượng:** Màn hình đăng nhập `I18nSignUpActivity` trên TikTok v46.6.3 hiển thị nút:
  `"Sử dụng số điện thoại/email/tên người dùng"` (bounds: `[186,852][930,906]`).
- **Bẫy cũ:** Hàm `choose_email_login` trong `social_reg_v1.py` chỉ tìm các chuỗi:
  `"Dùng số điện thoại/email"`, `"Dùng SĐT/email"`, `"Use phone/email"`, v.v.
- **Hệ quả:** Script login không nhận diện được nút để tap, dẫn đến treo hoặc timeout 600s ở bước chọn phương thức đăng nhập.
- **Khắc phục chuẩn:** Bổ sung chuỗi `"Sử dụng số điện thoại/email/tên người dùng"` vào danh sách tìm kiếm ưu tiên đầu tiên của `find_text_tap`.

## 2. Truyền file APK lớn qua ADB trên OneDrive
- Khi truyền các file APK lớn (>50MB như Outlook 100MB, ViChanger 120MB) trực tiếp từ đường dẫn OneDrive (`D:\OneDrive\apk-bank\...`), tiến trình ADB Stream install hoặc ADB push dễ bị timeout / nghẽn I/O.
- **Giải pháp:** Luôn copy file APK lớn về ổ đĩa cục bộ (`D:\Taadaa\tools\`) trước khi chạy `adb install` để đảm bảo tốc độ cài đặt tức thì (<15s) và không làm timeout worker.

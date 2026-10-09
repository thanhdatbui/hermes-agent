# TikTok Login Fail-Closed on Password Failure & Rate Limit

## 🛑 Quy tắc An toàn Bất di bất dịch (User Invariant)
Khi đăng nhập TikTok trên máy farm qua ADB:
- **CẤM TUYỆT ĐỐI thử lại mật khẩu lần 2 nếu lần 1 không vượt qua được**.
- Thử sai mật khẩu liên tục trên cùng 1 thiết bị hoặc IP sẽ dẫn đến:
  1. TikTok tạm khóa tính năng đăng nhập trên app (`Bạn đã truy cập dịch vụ của chúng tôi quá thường xuyên`).
  2. Bị ép xác minh danh tính phức tạp qua SparkActivity hoặc khóa vĩnh viễn tài khoản.

---

## 🛠 Triển khai trong `tiktok_login_v1.py` & `drive_login_screens`

1. **Phát hiện dấu hiệu lỗi mật khẩu từ UI**:
   Kiểm tra chuỗi giao diện XML không dấu:
   ```python
   WRONG_PASS_HINTS = [
       "mat khau khong dung", "mat khau khong chinh xac", "sai mat khau",
       "incorrect password", "wrong password", "thu lai mat khau",
       "khong dung voi tai khoan", "thu qua so lan", "qua nhieu lan"
   ]
   if any(w in flat for w in WRONG_PASS_HINTS):
       log(f"   [AUTH_BLOCKED] 🛑 Phát hiện sai mật khẩu hoặc bị rate limit TikTok cho {account.get('id') or email}! DỪNG NGAY BẢO VỆ TÀI KHOẢN!")
       screenshot(device_id, f"wrong_pass_{stt or 'x'}_{re.sub(r'[^A-Za-z0-9._-]+', '_', account['id'] or email)}")
       account.setdefault("issues", []).append("WRONG_TIKTOK_PASSWORD")
       return
   ```

2. **Cờ `password_submitted` chống thử lại**:
   - Khởi tạo `password_submitted = False` ở đầu hàm `drive_login_screens()`.
   - Khi `fill_password_and_login()` được gọi thành công 1 lần -> gán `password_submitted = True`.
   - Nếu ở vòng lặp sau, màn hình vẫn còn ở `PASSWORD_HINTS`:
     ```python
     if password_submitted:
         log("   [AUTH_BLOCKED] 🛑 Mật khẩu đã được điền nhưng TikTok vẫn ở màn hình password! CẤM ĐIỀN LẠI LẦN 2! DỪNG NGAY!")
         screenshot(device_id, f"wrong_pass_repeat_{stt or 'x'}_{re.sub(r'[^A-Za-z0-9._-]+', '_', account['id'] or email)}")
         account.setdefault("issues", []).append("PASSWORD_RETRY_BLOCKED")
         return
     ```
   - Chụp ảnh bằng chứng và thoát ngay lập tức, báo cáo lên hệ thống thay vì tiếp tục gõ lại.

# TikTok Login: Ưu tiên TikTok ID + Pass + TOTP né Email OTP và Google reCAPTCHA

## Bối cảnh & Hiện tượng lỗi (2026-09-22)
- Khi nạp tài khoản TikTok (ví dụ `tranngan767` trên Máy 1), script `tiktok_login_v1.py` cũ mặc định điền `account['login_email']` (`tranngan03012004@gmail.com`) vào ô "Email/tên người dùng".
- Hệ quả chết người:
  1. TikTok thấy nhập email sẽ tự động chọn cơ chế gửi mã xác minh 6 số (OTP) về hòm thư Gmail/Hotmail thay vì cho nhập mật khẩu.
  2. Nếu thiết bị Android chưa được thêm tài khoản Gmail này vào hệ điều hành (`dumpsys account`), script cố mở Gmail app để lấy mã nhưng không thấy hòm thư.
  3. Nếu cố gắng thêm Gmail vào máy qua `ADD_ACCOUNT_SETTINGS`, Google bật màn hình reCAPTCHA (chọn ảnh xe buýt, trụ cứu hỏa...) hoặc chặn "Không thể xác minh tài khoản", gây tắc nghẽn 100% tự động hóa.

## Quy tắc vàng: Đăng nhập bằng TikTok ID (Username)
- Màn hình đăng nhập của TikTok có tiêu đề là **"Email/tên người dùng"** (Email / Username / TikTok ID).
- Khi nhập **TikTok Username** (ví dụ `tranngan767`):
  1. TikTok chuyển thẳng sang màn hình **Nhập mật khẩu** (`fill_password_and_login`).
  2. Sau khi nhập mật khẩu TikTok (`account['tiktok_pass']`), nếu tài khoản đã bật 2FA, TikTok sẽ hiện màn hình **Ứng dụng xác thực (Authenticator App)**.
  3. Script tự động sinh mã TOTP 6 số từ `account['twofa']` bằng thư viện `pyotp.TOTP(secret.replace(' ', '').upper()).now()` và điền vào.
  4. Đăng nhập thành công ngay lập tức mà **HOÀN TOÀN KHÔNG CẦN CHẠM VÀO GMAIL/OUTLOOK** và **NÉ TRIỆT ĐỂ GOOGLE RECAPTCHA**.

## Patch logic chuẩn trong `tiktok_login_v1.py`:
```python
# Thay vì hardcode login_email:
# fill_existing_email_and_continue(device_id, account["login_email"], stt=stt)

# Ưu tiên đăng nhập bằng TikTok ID nếu đã có password trong Excel:
login_target = (account.get("id") or "").strip() if (account.get("id") and account.get("tiktok_pass")) else account["login_email"]
fill_existing_email_and_continue(device_id, login_target, stt=stt)
```

## Checklist kiểm tra trước khi chạy login:
1. Kiểm tra tài khoản trong `taikhoan_dat_v2_updated .xlsx`: đã có đủ `id`, `tiktok_pass`, `twofa` chưa.
2. Nếu đủ cả 3: dùng thẳng flow TikTok ID + Password + TOTP.
3. Chỉ dùng email login khi tài khoản thiếu mật khẩu TikTok hoặc bắt buộc phải reset pass qua email.

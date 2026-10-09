# TikTok Login: Cho Phép Usable Khi Có ID + Pass + TOTP Dù Thiếu Mail Pass (2026-09-24)

## Bối Cảnh
Trong script `D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py`, hàm `load_tracking_accounts_for_stt` trước đây yêu cầu tài khoản phải có đủ cả `tiktok_pass`, `mail_pass` và `login_email` thì mới gán cờ `usable = True`.
- Nếu thiếu `mail_pass`, tài khoản bị gắn nhãn `[CHECK]` (`issues=missing_mail_pass`) và bị từ chối chạy khi gọi `--email <id>` hoặc `--all`.

## Thực Tế Kỹ Thuật
- Các tài khoản đăng ký bằng Hotmail sau thời gian ngâm đã được kích hoạt **Mã xác thực 2 bước (2FA App / TOTP Secret)**.
- Khi đăng nhập, quy trình đăng nhập TikTok sử dụng:
  1. TikTok ID (hoặc Email)
  2. Mật khẩu TikTok (`tiktok_pass`)
  3. Mã 6 số từ ứng dụng xác thực (`twofa` TOTP Secret)
- Toàn bộ quy trình hoàn toàn không gửi hay đòi mã OTP qua email, do đó **không cần mật khẩu hòm thư (`mail_pass`)** vẫn đăng nhập thành công 100%.

## Quy Tắc Cập Nhật Trong `tiktok_login_v1.py`
```python
has_id_pass = bool(account["id"]) and bool(account["tiktok_pass"])
has_mail_auth = bool(account["login_email"]) and bool(account["mail_pass"])
account["usable"] = (
    (has_id_pass or has_mail_auth)
    and "email_invalid" not in account["issues"]
)
```
- Khi tài khoản có đầy đủ ID + Pass (và TOTP nếu có), script tự động đánh dấu `[OK]` và cho phép tiến hành login trực tiếp.

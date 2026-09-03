# Reconcile Missing 2FA Hotmail / Outlook Flow (2026-08-22)

## Hiện tượng (Máy 4)
- Script: `reconcile_tiktok_accounts.py` chạy cho máy 4.
- Target account: `bronsontruss38` (Row 4 / Tik4, mail: `BronsonTrussel163815@hotmail.com`).
- Ban đầu lỗi: `login failure at account bronsontruss38; stopped this machine and preserved current state; failed_login_count=1; account_not_registered_no_2fa_count=0; account_failures=bronsontruss38:restart-AccountInventoryError`.

## Nguyên nhân
1. **Thiếu 2FA secret trong workbook:**
   - Trong `taikhoan_dat_v2_updated .xlsx`, cột `2FA` của nick `bronsontruss38` là `None` (trống).
2. **Thách thức đăng nhập (Challenge):**
   - Khi TikTok login tài khoản Hotmail/Outlook không có 2FA secret, app TikTok yêu cầu mã xác minh OTP gửi về email.
   - App Outlook trên thiết bị chưa đăng nhập hòm thư Hotmail nên không tự lấy được OTP lúc đầu.

## Quy trình xử lý chuẩn
1. **Đăng nhập Hotmail vào app Outlook:**
   - Chạy `flows/login_outlook_one_machine.py --machine 4 --serial <serial> --email <mail> --user-authorized`.
   - Lưu ý: Trong `login_outlook_app`, nếu sau khi nhập email xuất hiện màn hình `ChooseAccountActivity` ("Chọn loại tài khoản") -> Bắt buộc tap `_tap_outlook_app_add_account_entry` vào entry Outlook để sang form password.
2. **Đăng nhập TikTok qua OTP Outlook:**
   - Chạy `login_one_account` trong `tiktok_login_v1.py` -> Nhập email -> App gửi OTP -> Reader đọc OTP từ Outlook app -> Điền 6 số -> Đăng nhập thành công.
3. **Nghiệm thu & Dọn dẹp:**
   - Mở Account Switcher kiểm tra đủ 4/4 nick trên máy.
   - `am force-stop` đóng các app, đưa máy về Home Screen và giải phóng lock file sạch sẽ.

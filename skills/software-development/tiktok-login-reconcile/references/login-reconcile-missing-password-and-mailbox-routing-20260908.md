# TikTok Login Reconcile: Missing Password Gate & Mailbox App Routing (2026-09-08)

## 1. Cấm Tuyệt Đối Viết Script Login Ad-hoc (User Correction)
- **Triệu chứng:** Khi gặp lỗi kẹt login hoặc cần nạp nick cho máy, subagent tự ý viết script Python tạm (`login_m3_exec.py`) hardcode tọa độ click và sinh mã TOTP điền bừa vào ô OTP Email.
- **Hậu quả:** Gây lỗi xác minh ("Lỗi mã xác minh email"), làm hỏng phiên, bị user khiển trách: *"Ghi clgt. T có làm script tiktok log in r mà???"*.
- **Quy tắc:** BẮT BUỘC dùng runner chính thức của farm:
  - `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <stt> --email <email> --ss`
  - Hoặc `reconcile_tiktok_accounts.py` từ repo `tiktok-log-in`.

## 2. Lỗi Missing Password Trong Tracking Chặn Full-Machine Reconcile
- **Triệu chứng:** Chạy `reconcile_tiktok_accounts.py` cho một máy (vd: Máy 03) bị dừng ngay lập tức với `status: FINAL_BLOCKED`, reason:
  `AccountInventoryError: machine <N>: TikTok ID/password is unavailable for <account_id>`
- **Nguyên nhân:**
  Trong `login_runner/account_reconcile.py`, hàm `_selected_missing_accounts` duyệt qua toàn bộ các tài khoản bị thiếu trên thiết bị (so với `taikhoan_run_safe.xlsx`). Nếu có BẤT KỲ tài khoản nào trong file Excel `taikhoan_dat_v2_updated .xlsx` có cột Mật khẩu TikTok (cột D) rỗng (`None`), hàm sẽ raise `AccountInventoryError` và chặn toàn bộ quá trình reconcile của máy, dù các tài khoản khác đều có pass đầy đủ.
- **Xử lý:**
  1. Kiểm tra cột D của tài khoản báo lỗi. Nếu tài khoản reg qua mail có mật khẩu mail (cột G), tính toán pass qua `make_tiktok_password(mail_pass)` để bổ sung vào cột D.
  2. Hoặc nạp lẻ từng tài khoản bằng lệnh:
     `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <stt> --email <target_email> --ss`

## 3. Lệch Kênh Đọc OTP: Hotmail Lưu Trong Ứng Dụng Gmail
- **Triệu chứng:** Chạy `tiktok_login_v1.py` cho nick dùng Hotmail (vd: `segovkibido@hotmail.com`), script phát hiện màn hình OTP, tự động mở app Outlook trên máy và dừng với lỗi `STOPPED: OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND`.
- **Nguyên nhân:**
  Hàm `handle_tiktok_email_otp` chia nhánh cứng: `email.endswith("@gmail.com")` thì mở Gmail app, còn lại mở Outlook app. Nhưng trên thực tế tại các máy farm (như Máy 03), tài khoản Hotmail đã được add thẳng vào ứng dụng **Gmail** của Android (hiển thị trong `live_gmail_accounts(device_id)["emails"]`), còn ứng dụng Outlook chưa được đăng nhập tài khoản này.
- **Xử lý:**
  - Kiểm tra các email đang online trong Gmail app trước bằng `live_gmail_accounts(device_id)`.
  - Nếu email Hotmail mục tiêu đã có sẵn trong Gmail app, ưu tiên lấy OTP qua luồng Gmail app hoặc đăng nhập nick `@gmail.com` trước để khôi phục phiên TikTok trên máy.

## 4. Fix Thiếu Import `ADB_PATH` Trong `tiktok_login_v1.py`
- Dòng 604 gọi `require_android_vpn(AdbClient(adb_path=ADB_PATH if "ADB_PATH" in globals() else "adb"))`.
- Nếu file thiếu `ADB_PATH` trong khối `from social_reg_v1 import ...`, script sẽ dùng lệnh `"adb"` chung của hệ thống thay vì `C:\Program Files (x86)\xiaowei\tools\adb.exe`, gây lỗi `adb executable not found: adb`.
- Bắt buộc import `ADB_PATH` ở cả 2 khối try/except đầu file `tiktok_login_v1.py`.

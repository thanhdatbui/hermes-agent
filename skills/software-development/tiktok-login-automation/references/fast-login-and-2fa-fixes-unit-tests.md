# Fast Login & 2FA Fixes Unit Test Patterns (Tiktok_Reg)

## 1. Mục tiêu & Phạm vi (Test File: `D:/Taadaa/Tiktok_Reg/tests/test_fast_login_and_2fa_fixes.py`)
Kiểm thử isolated, 100% offline (mock toàn bộ ADB, UI XML và openpyxl), thời gian thực thi < 5 giây (10/10 tests PASS) để bảo vệ các fix quan trọng và structured telemetry trong `tiktok_login_v1.py` và `social_reg_v1.py`.

---

## 2. Quy tắc Logic & Test Contracts

### 2.1. `is_auth_landing_screen(xml)` (`tiktok_login_v1.py`)
- **Tích cực (Positive):**
  - Màn hình đăng ký: `"dang ky tiktok"` kết hợp với `"ban da co tai khoan"` hoặc `"tiep tuc voi email"`.
  - Màn hình đăng nhập: `"dang nhap"` kết hợp với `"tiep tuc voi email"`, `"email hoac tiktok id"`, `"email/ten nguoi dung"`, hoặc `"dien thoai"`.
  - Trường nhập trực tiếp: `"email hoac tiktok id"` hoặc `"nhap dia chi email"`.
- **Tiêu cực (Negative):**
  - Màn hình Feed ("Dành cho bạn"), Profile ("Chỉnh sửa hồ sơ", "Đang theo dõi") không được nhận nhầm là auth landing.

### 2.2. `ensure_login_entry_screen(device_id, stt)` (`tiktok_login_v1.py`)
- **Bỏ qua nếu đã ở Auth Landing:** Khi `is_auth_landing_screen(xml)` trả về `True`, hàm return ngay lập tức mà không gọi `go_to_profile` hay thao tác thừa.
- **Xử lý One-Tap / "Chào mừng bạn trở lại":** Nếu phát hiện `"chao mung ban tro lai"`, `"welcome back"` hoặc `"them tai khoan khac"`, tự động gọi `find_text_tap("Thêm tài khoản khác", ...)` và return sớm, tránh vòng lặp mở profile không cần thiết.
- **Telemetry Emission:** Ghi log telemetry khi bypass thành công:
  `[telemetry:login-entry] action=one_tap_bypass device={device_id} result=success`
- **Test:** `test_ensure_login_entry_screen_telemetry_emission` verify mock log nhận đúng chuỗi này.

### 2.3. Ưu tiên 2FA hơn Password trong `drive_login_screens`
- **Quy tắc:** Khi UI xuất hiện đồng thời cả gợi ý 2FA (`TWOFA_HINTS`, e.g. "ứng dụng xác thực", "2-step verification") và mật khẩu (`PASSWORD_HINTS`), luồng xử lý PHẢI dispatch `handle_tiktok_authenticator_2fa` trước và bỏ qua `fill_password_and_login` trong vòng lặp đó.
- **Telemetry Emission:** Ghi nhận:
  `[telemetry:auth-screen] action=2fa_priority_dispatched round={round_idx}`
- **Test:** `test_drive_login_screens_prioritizes_2fa_over_password` mock UI chứa cả hai hints; assert `handle_tiktok_authenticator_2fa` được gọi, `fill_password_and_login` không bị gọi và telemetry round 1 được log.

### 2.4. `resume_one_account` xử lý trực tiếp Auth Landing (`SignUpOrLoginActivity`)
- **Quy tắc:** Khi nối tiếp từ màn hiện tại mà gặp màn `SignUpOrLoginActivity` hoặc màn nhập email/TikTok ID, tự động chọn email login, trích xuất target (`account['id']` nếu có pass, ngược lại `login_email`), và gọi `fill_existing_email_and_continue`.
- **Telemetry Emission:**
  `[telemetry:resume-login] action=email_form_detected device={device_id} target={login_target}`
- **Test:** `test_resume_one_account_handles_auth_landing_directly` mock màn `SignUpOrLoginActivity`, assert `fill_existing_email_and_continue` được gọi đúng target và telemetry được phát ra.

### 2.5. Tiêu chí Account Usable (`load_tracking_accounts_for_stt`)
- **Điều kiện Usable:**
  - Có `(id + tiktok_pass)` HOẶC `(login_email + mail_pass)`.
  - Không chứa cờ `"email_invalid"` trong `account["issues"]`.
- **Lưu ý về `_infer_login_email`:**
  - Nếu raw email không có `@` nhưng khớp regex `[A-Za-z0-9._%+-]+`, hàm tự suy đoán thành `<email>@gmail.com` và gắn issue `email_inferred_gmail` (vẫn hợp lệ, usable).
  - Chỉ khi raw email chứa ký tự không hợp lệ (ví dụ: khoảng trắng, ký tự đặc biệt) mới bị gắn `email_invalid` và vô hiệu hóa (`usable = False`).

### 2.6. `_device_epoch_seconds(device_id)` (`social_reg_v1.py`)
- **Host NTP Sync:** Luôn trả về `int(time.time())` của máy chủ host, tuyệt đối không truy vấn đồng hồ điện thoại qua ADB shell date vì Samsung S7 thường xuyên lệch ~28s làm sai lệch mã TOTP 2FA.

### 2.7. `dismiss_profile_overlays(device_id)` (`social_reg_v1.py`)
- **Bảo vệ Account Dropdown Sheet:** Khi màn hình xuất hiện bottom sheet (`fxs` hoặc `"dang ho tro:"`), chỉ dismiss khi `_account_dropdown_open_xml(xml)` là `False`.
- Nếu `_account_dropdown_open_xml(xml)` là `True` (dropdown chuyển tài khoản đang mở), giữ nguyên không dismiss.

---

## 3. Cạm bẫy Cross-Drive Path trên Windows
- **Triệu chứng lỗi:** Chạy `python -m unittest D:/Taadaa/Tiktok_Reg/tests/...` khi terminal CWD đang ở `C:\Users\...` sẽ quăng:
  `ValueError: path is on mount 'D:', start on mount 'C:'` do `unittest` gọi `os.path.relpath` qua 2 ổ đĩa khác nhau trên Windows.
- **Giải pháp chuẩn:**
  - Dùng `pytest`: `python -m pytest "D:/Taadaa/Tiktok_Reg/tests/test_fast_login_and_2fa_fixes.py" -q`
  - Pytest xử lý tốt absolute cross-drive paths và thực thi hoàn tất trong ~4s (10/10 tests PASS).

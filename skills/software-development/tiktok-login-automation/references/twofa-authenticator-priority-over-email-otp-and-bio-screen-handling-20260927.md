# Quy tắc Ưu tiên 2FA Authenticator trước Fallback OTP Email & Phân loại Màn hình 2FA (2026-09-27)

## Bối cảnh & Hiện tượng lỗi
1. **Lỗi ngộ nhận 2FA Email thành Authenticator TOTP**:
   - Khi TikTok hiển thị màn hình `Xác minh 2 bước`, mặc định giao diện thường chọn phương thức gửi mã về Email (`Sử dụng liên kết này hoặc nhập mã được gửi đến a***@gmail.com`).
   - Màn hình này có chứa tiêu đề `Xác minh 2 bước`. Nếu classifier regex bắt lỏng lẻo cụm từ `xác minh 2 bước` làm Authenticator App, script sẽ lấy mã TOTP 6 số từ secret Excel điền vào ô mã OTP Email.
   - Kết quả: TikTok từ chối liên tiếp 3 lần (`Mã xác minh email đã hết hạn / không hợp lệ`), gây dừng quy trình giả tạo.

2. **Khẩu lệnh chỉ đạo của User**:
   - *"thì chọn sử dụng phương thức khác r dùng 2fa đi, luôn ưu tiên 2fa trước otp mail sau"*
   - *"Cập nhật script luôn đi 2fa ưu tiên r ms fallback sang otp"*

## Giải pháp Chuẩn hóa & Pattern Code

### 1. Luôn tự động chuyển sang Authenticator App nếu đang ở luồng Email OTP
Trên màn hình `Xác minh 2 bước` đang gửi về Email, luôn có nút:
- `Sử dụng phương thức khác >` (`Su dung phuong thuc khac` / `Use another method`, thường ở tọa độ `[408, 1039]` hoặc `[408, 1098]`).
Khi tap vào nút này, TikTok mở popup `Chọn phương thức xác minh` chứa:
- `Trình xác thực` / `Ứng dụng xác thực` (`Authenticator app`, thường ở `(540, 1662)`).

```python
# social_reg_v1.py - handle_tiktok_authenticator_2fa
auth_markers = ["ung dung xac thuc", "authenticator app", "google authenticator"]
# Nếu đang ở màn 2FA nhưng là luồng Email OTP ("gửi đến", "email"), tap "Sử dụng phương thức khác" để chuyển sang Authenticator
if not any(h in flat for h in auth_markers) and (any(h in flat for h in ["gui den", "email"]) or "xac minh 2 buoc" in flat):
    log("[2fa-app] Email OTP screen -> switch to another method")
    if not find_text_tap(device_id, "Sử dụng phương thức khác", "Su dung phuong thuc khac", "Use another method", wait=0.5):
        tap(device_id, 408, 1098, wait=0.5)
    time.sleep(1.5)
    if not find_text_tap(device_id, "Trình xác thực", "Trinh xac thuc", "Ứng dụng xác thực", "Ung dung xac thuc", "Authenticator App", wait=0.5):
        log("[2fa-app] Khong thay lua chon Authenticator App")
        return False
    time.sleep(1.5)
    xml = get_ui_xml(device_id)
    flat = strip_accents(xml).lower()
```

### 2. Thứ tự ưu tiên điều phối trong `drive_login_screens()`
Luôn cố gắng gọi `handle_tiktok_authenticator_2fa()` trước. Nếu thành công -> tiếp tục. Nếu không thể chuyển sang Authenticator (tài khoản không có secret hoặc giao diện không có mục Trình xác thực) -> mới fallback sang `handle_tiktok_email_otp()`.

```python
# tiktok_login_v1.py - drive_login_screens()
if any(h in flat for h in TWOFA_AUTHENTICATOR_HINTS) or any(h in flat for h in TWOFA_GENERIC_HINTS):
    log(f"[telemetry:auth-screen] action=authenticator_2fa_dispatched round={round_idx}")
    auth_ok = handle_tiktok_authenticator_2fa(device_id, email, stt=stt)
    if auth_ok:
        time.sleep(D_LONG)
        continue
    # Nếu không có Authenticator / không chuyển được, fallback sang Email OTP
    log(f"[telemetry:auth-screen] action=fallback_email_otp_2fa round={round_idx}")
    handle_tiktok_email_otp(device_id, email, account["mail_pass"], stt=stt)
    time.sleep(D_LONG)
    continue
```

### 3. Dismiss màn hình Onboarding 'Tiểu sử' (Bio Screen)
Sau khi login thành công, TikTok có thể hiện màn hình onboarding `Tiểu sử` (Bio screen: `Bạn có thể chỉnh sửa tiểu sử bất cứ lúc nào`, có nút `Hủy` tại `[24,72][167,204]`).
Bắt buộc thêm kiểm tra vào `handle_post_auth_screens()`:
```python
if "tieu su" in flat or "chinh sua tieu su" in flat:
    log(f"[8b-{_r}] Bio screen detected -> tap Huy/Bo qua")
    if not find_text_tap(device_id, "Hủy", "Huy", "Bỏ qua", "Bo qua", "Skip", wait=2):
        tap(device_id, 95, 138, wait=2)
    continue
```

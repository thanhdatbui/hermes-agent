# TikTok Login: Ưu tiên Đăng nhập bằng TikTok ID + Password né reCAPTCHA Google & OTP Mail (2026-09-22)

## 1. Bối cảnh & Nguyên nhân Gốc rễ

Khi đăng nhập tài khoản TikTok đã tồn tại trên thiết bị farm (bằng script `tiktok_login_v1.py` hoặc thao tác tay):
- **Bẫy điền Email:** Nếu nhập địa chỉ email (`account['login_email']`), TikTok mặc định chuyển sang luồng gửi mã xác minh OTP 6 chữ số về hòm thư (`registered_otp`).
- **Hệ quả dây chuyền (Bẫy con gà - quả trứng):**
  1. Hộp thư Gmail/Hotmail thường chưa được đăng nhập trên ứng dụng Gmail/Outlook của thiết bị Android đó.
  2. Script cố gắng thêm tài khoản Google vào máy qua Android Settings (`ADD_ACCOUNT_SETTINGS`).
  3. Google nhận diện thiết bị/IP proxy lạ và kích hoạt ngay màn hình bảo vệ danh tính: **bắt giải reCAPTCHA hình ảnh** (chọn xe buýt, trụ cứu hỏa...) hoặc chặn với thông báo *"Google không thể xác minh rằng tài khoản này là của bạn"*.
  4. Quá trình tự động hóa bị nghẽn hoàn toàn, dẫn đến fail-stop hoặc timeout.

---

## 2. Giải pháp Triệt để: Đăng nhập bằng TikTok ID (Username)

Ô nhập liệu đầu tiên của TikTok có tiêu đề: **"Email/tên người dùng"** (Email or TikTok ID).

### Cơ chế hoạt động:
1. **Nếu điền TikTok ID (`account['id']`):**
   - TikTok nhận diện đây là tên người dùng của tài khoản đã tồn tại.
   - TikTok chuyển ngay sang màn hình **"Nhập mật khẩu" (`Nhập mật khẩu` / `f7l`)**, hoàn toàn KHÔNG kích hoạt luồng gửi OTP về email!
2. **Xác thực mật khẩu:**
   - Điền mật khẩu TikTok (`account['tiktok_pass']`) từ Excel Master (`taikhoan_dat_v2_updated .xlsx`).
3. **Xác thực 2FA (nếu có):**
   - Nếu tài khoản đã bật 2-Step Verification dạng Authenticator App, TikTok sẽ hỏi mã 6 số.
   - Script tự động đọc `twofa_secret` từ cột 2FA trong Excel và sinh mã TOTP tức thì:
     ```python
     import pyotp
     code = pyotp.TOTP(secret.replace(" ", "").upper()).now()
     ```
   - Điền mã TOTP và bấm tiếp tục.

👉 **Kết quả:** Vào thẳng trang chủ TikTok / Profile trong vòng 10 giây, **bảo toàn 100% không đụng tới Google Account hay hòm thư mail**, né sạch reCAPTCHA.

---

## 3. Bản vá Chuẩn trong `D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py` (Commit `466103d`)

Tại hàm `login_one_account`:
```python
# OLD:
ensure_login_entry_screen(device_id, stt=stt)
choose_email_login(device_id)
fill_existing_email_and_continue(device_id, account["login_email"], stt=stt)
drive_login_screens(device_id, account, stt=stt)

# NEW (Vá chuẩn 2026-09-22):
ensure_login_entry_screen(device_id, stt=stt)
choose_email_login(device_id)
# Ưu tiên TikTok ID + Pass né OTP email và reCAPTCHA Google
login_target = (account.get("id") or "").strip() if (account.get("id") and account.get("tiktok_pass")) else account["login_email"]
fill_existing_email_and_continue(device_id, login_target, stt=stt)
drive_login_screens(device_id, account, stt=stt)
```

---

## 4. Checklist Kiểm chứng khi Nạp Tài khoản vào Máy:
1. **Kiểm tra thông tin tài khoản trong Excel Master:**
   - Có `id` (TikTok username)?
   - Có `tiktok_pass`?
   - Có `twofa` (Secret 32 ký tự)?
2. **Kiểm tra trạng thái Switcher trên máy:**
   - Bung Switcher tại Profile header `(500, 290)` hoặc qua menu Cài đặt $\rightarrow$ Chuyển đổi tài khoản `(540, 1494)`.
   - Nếu đã đủ 8 nick (`len(accounts) == 8`): DỪNG NGAY, raise `MACHINE_FULL_8_ACCOUNTS`.
   - Nếu `< 8` nick: Chạy lệnh nạp nick qua TikTok ID.

---

## 5. Mở Khóa Kiểm Tra Usable Khi Thiếu Mail Pass (Fix 2026-09-24)

### Bẫy logic cũ trong `load_tracking_accounts_for_stt`:
Trước đây code kiểm tra độ khả dụng (`usable`) của tài khoản:
```python
# CŨ: Đòi hỏi bắt buộc phải có cả mail_pass
account["usable"] = (
    bool(account["id"])
    and bool(account["tiktok_pass"])
    and bool(account["mail_pass"])
    and bool(account["login_email"])
    and "email_invalid" not in account["issues"]
)
```
- **Hậu quả**: Nếu tài khoản chỉ có `id`, `tiktok_pass` và `twofa` nhưng cột `mail_pass` trống (như các nick reg qua Hotmail ngâm lâu hoặc chỉ lưu pass TT), tài khoản bị gắn cờ `[CHECK] issues=missing_mail_pass` và `usable=False`. Khi chạy `tiktok_login_v1.py` bị chặn với lỗi `Khong co account nao du info de login` hoặc từ chối login.
- **Bản vá chuẩn hóa**: Khi có đủ TikTok ID + TikTok Password, tài khoản hoàn toàn đủ điều kiện đăng nhập độc lập qua ID+Pass+TOTP mà không cần password của mail:
```python
has_id_pass = bool(account["id"]) and bool(account["tiktok_pass"])
has_mail_auth = bool(account["login_email"]) and bool(account["mail_pass"])
account["usable"] = (
    (has_id_pass or has_mail_auth)
    and "email_invalid" not in account["issues"]
)
```

---

## 6. Xử Lý Màn Hình One-Tap "Chào mừng bạn trở lại" Trong `ensure_login_entry_screen` (2026-09-24)

### Triệu chứng
Khi app TikTok đã có tài khoản lưu hoặc sau khi mở màn hình login, TikTok hiển thị màn One-tap Login với tiêu đề *"Chào mừng bạn trở lại"* (hoặc *"Welcome back"* / avatar lưu kèm nút Tiếp tục) và một nút nhỏ *"Thêm tài khoản khác"*. Nếu script không nhận diện màn này, nó sẽ thử tap vào profile tab hoặc dropdown khiến luồng bị kẹt hoặc chuyển sai trang.

### Giải pháp
Trong `ensure_login_entry_screen(device_id)`:
```python
flat = strip_accents(xml).lower()
if any(k in flat for k in ["chao mung ban tro lai", "welcome back"]) or "them tai khoan khac" in flat:
    log("[login-entry] Phat hien man One-tap / Chao mung ban tro lai -> tap Them tai khoan khac de vao form login")
    if find_text_tap(device_id, "Thêm tài khoản khác", "Them tai khoan khac", "Add another account", wait=D_LONG):
        time.sleep(D_LONG)
        return
```

---

## 7. Phục Hồi Nick Switcher Bị Văng (`ACCOUNT_SWITCHER_FAILED`) & Kế Thừa Parent Lock

Khi chạy batch đăng video hoặc đổi avatar bị dừng với lỗi:
`[ACCOUNT_SWITCHER_FAILED] ACCOUNT_READY verify failed: ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account. Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa...`

### Quy trình phục hồi chuẩn:
1. **Kiểm tra Account Switcher trên máy qua XML / Screencap**:
   - Nếu trong Switcher có 7/8 nick và thiếu chính xác nick mục tiêu (ví dụ `@bmwarclxp1f`): Đây là trường hợp session bị out hoặc nick chưa được nạp vào máy.
2. **Kích hoạt nạp bù tài khoản bằng lệnh chuẩn**:
   ```bash
   python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <ID_HOAC_EMAIL> --allow-parent-lock --ss
   ```
   - Flag `--allow-parent-lock` bắt buộc phải có nếu máy đang được giữ lock bởi cron/scheduler mẹ (`tiktok-luot nuoi acc`), tránh lỗi exit code 2 `NEEDS_USER_DECISION`.
3. Sau khi lệnh nạp bù hoàn tất (`[login-success] home feed UI proof`), chạy lại batch upload video hoặc đổi avatar.

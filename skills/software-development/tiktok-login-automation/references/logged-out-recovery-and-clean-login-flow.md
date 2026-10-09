# Quy Trình Đăng Nhập Khôi Phục Trên Máy Đã Bị Đăng Xuất Hoàn Toàn (Logged-Out Device Recovery Flow)

Đúc kết từ sự cố vận hành ngày 08/09/2026 trên máy STT 03: Sau khi bị đăng xuất khỏi tài khoản, toàn bộ multi-account session trên app TikTok bị rơi về trạng thái chưa đăng nhập (Logged-Out).

---

## 1. Hai Cạm Bẫy Của Runner Tự Động Khi Máy Đang Ở Trạng Thái Logged-Out

Khi máy không còn tài khoản nào active trên TikTok, cả 2 script runner chuẩn đều có bẫy logic nếu không được chuẩn bị trước:

### A. Cạm bẫy 1: `reconcile_tiktok_accounts.py` báo `TikTok startup was not ready`
- **Nguyên nhân:** Runner chạy `collect_device_inventory()` để kiểm kê danh sách nick trên máy trước khi login.
  - Hàm `_start_tiktok_and_wait()` yêu cầu nhận diện được thanh điều hướng đáy (`has_navigation_surface`). Khi app ở modal *"Chào mừng bạn trở lại"* hoặc màn chọn đăng nhập, thanh điều hướng bị che khuất -> runner ném lỗi:
    `AccountInventoryError: machine <stt>: TikTok startup was not ready`
  - Ngoài ra, hàm `open_account_switcher()` phụ thuộc vào việc có icon dropdown hoặc tên hiển thị trên header profile. Màn hình logged-out không có dropdown switcher -> kiểm kê thất bại.

### B. Cạm bẫy 2: `tiktok_login_v1.py` báo `[03_dropdown] Khong mo duoc account dropdown`
- **Nguyên nhân:** Hàm `ensure_login_entry_screen()` mặc định rằng máy đã có sẵn ít nhất 1 nick đăng nhập, cố gắng gọi `open_account_dropdown(device_id)` -> `tap_add_account()`.
  - Trên màn hình Hồ sơ trắng (Logged-Out Profile), nút dropdown switcher không tồn tại.
  - Sau khi `open_account_dropdown` fail, khối `except` kiểm tra `is_auth_landing_screen(xml)` cũng trả về `False` (do màn Hồ sơ trắng chứa text *"Đăng nhập vào tài khoản hiện có"* chứ không phải *"Tiếp tục với email"*).
  - Kết quả: Script crash `RuntimeError: [03_dropdown] Khong mo duoc account dropdown`.

---

## 2. Kịch Bản Điều Hướng Chuẩn (Deterministic Recovery Steps)

Để khôi phục đăng nhập an toàn từ trạng thái Logged-Out, kịch bản phải xử lý phân nhánh chính xác:

```
[Màn hình hiện tại]
   │
   ├── Nếu có modal "Chào mừng bạn trở lại" (id/ym3):
   │      └── Tap "Thêm tài khoản khác" (id/ym6, center 540, 1552)
   │
   └── Nếu ở màn Hồ sơ trắng ("Đăng nhập vào tài khoản hiện có"):
          └── Tap nút lớn "Đăng nhập" (id/czm, center 540, 1094)
                 └── Nếu hiện modal "Chào mừng", tap "Thêm tài khoản khác" (540, 1552)
                           │
                           ▼
          [Màn hình "Đăng nhập vào TikTok"]
          Tap "Sử dụng số điện thoại/email/tên người dùng" (center 540, 879)
                           │
                           ▼
          [Màn hình nhập Email / TikTok ID]
          Tap tab "Email / TikTok ID" (center 750, 300)
          Nhập email -> Tap "Tiếp tục"
                           │
                           ▼
          [Màn hình Mật khẩu]
          Nhập Password TikTok -> Tap "Đăng nhập"
                           │
                           ▼
          [Màn hình 2FA Authenticator (nếu có)]
          pyotp.TOTP(secret).now() -> Nhập 6 chữ số
                           │
                           ▼
          [Post-Auth Screens]
          Tap "Lưu" thông tin đăng nhập -> "Từ chối" đồng bộ danh bạ
                           │
                           ▼
          [Profile Root]
          Tap header bung Account Switcher -> Chụp ảnh nghiệm thu
```

---

## 3. Template Code Tự Động Hóa Login Nick Chuẩn (Zero-Hang)

```python
import time
import pyotp
import subprocess

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"

def recover_login_first_account(serial, email, password, totp_secret):
    def adb_tap(x, y):
        subprocess.run([ADB, "-s", serial, "shell", "input", "tap", str(x), str(y)], check=True)
        time.sleep(1.5)

    def adb_text(txt):
        subprocess.run([ADB, "-s", serial, "shell", "input", "text", txt], check=True)
        time.sleep(1.0)

    # 1. Mở màn chọn phương thức
    # Tap "Thêm tài khoản khác" (nếu ở modal Chào mừng)
    adb_tap(540, 1552)
    # Tap "Sử dụng số điện thoại/email/tên người dùng"
    adb_tap(540, 879)

    # 2. Chuyển sang tab Email & nhập
    adb_tap(750, 300)  # Tab Email/TikTok ID
    adb_tap(540, 420)  # Focus vào ô EditText
    adb_text(email)
    adb_tap(540, 700)  # Nút Tiếp tục / Next
    time.sleep(3.0)

    # 3. Nhập Password
    adb_tap(540, 420)  # Focus ô password
    adb_text(password)
    adb_tap(540, 700)  # Nút Đăng nhập
    time.sleep(4.0)

    # 4. Xử lý 2FA nếu được yêu cầu
    if totp_secret:
        code = pyotp.TOTP(totp_secret).now()
        # Tap vào ô OTP đầu tiên và gõ mã
        adb_tap(180, 500)
        adb_text(code)
        time.sleep(5.0)

    # 5. Xử lý Post-auth
    adb_tap(540, 1400) # Tap "Lưu" nếu có modal Lưu thông tin
    time.sleep(2.0)
```

---

## 4. Quy Chuẩn Nghiệm Thu Ảnh Sau Khôi Phục (Proof Gate)
- Sau khi đăng nhập thành công tài khoản đầu tiên:
  1. Vào tab **Hồ sơ** ở góc dưới bên phải (`972, 1857`).
  2. Tap vào display name ở header đỉnh màn hình (`350, 150` hoặc resource-id `id/su7`) để bung **Bottom Sheet "Chuyển đổi tài khoản" (Account Switcher)**.
  3. Chụp ảnh màn hình lưu vào `D:/Taadaa/reports/stt<stt>_reconcile_proof.png`.
  4. Trả về đúng link `MEDIA:<path>` dòng riêng. CẤM gửi ảnh màn hình Settings hay popup.

# Bẫy Màn hình One-Tap Fast Login, 2FA Checkbox Substring & Giới hạn 8 Nick Switcher (2026-09-24)

## 1. Hiện tượng & Bối cảnh (Farm Kibe Máy 1 ca nuôi feed 14:00)
- Ca nuôi phát hiện Máy 1 thiếu nick Row 4 (`ginnyhanstei80`), trong Switcher chỉ có 7 tài khoản, vị trí thứ 8 hiển thị nút *"Thêm tài khoản"*.
- Lệnh nạp bù tự động `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py 1 --email ginnyhanstei80 --ss --allow-parent-lock` bị **TIMEOUT 180s/240s** do liên hoàn 5 bẫy code.

---

## 2. Chi tiết 5 Bẫy Code & Giải pháp Đã Chứng Minh Thành Công

### Bẫy 1: Màn hình One-Tap Fast Login ("Chào mừng bạn trở lại")
- **Hiện tượng:** TikTok lưu cache tài khoản cũ (`ahmetsguthe17`), hiển thị modal *"Chào mừng bạn trở lại"* kèm nút *"Thêm tài khoản khác"* (`com.ss.android.ugc.trill:id/z3k`).
- **Nguyên nhân:** Hàm `ensure_login_entry_screen` trong `tiktok_login_v1.py` chỉ kiểm tra `is_auth_landing_screen`. Khi không khớp, nó gọi `go_to_profile(device_id)` mặc dù màn hình này không có tab Profile, gây lạc flow.
- **Giải pháp:**
  ```python
  flat = strip_accents(xml).lower()
  if any(k in flat for k in ["chao mung ban tro lai", "welcome back"]) or "them tai khoan khac" in flat:
      log("[login-entry] Phat hien man One-tap / Chao mung ban tro lai -> tap Them tai khoan khac de vao form login")
      if find_text_tap(device_id, "Thêm tài khoản khác", "Them tai khoan khac", "Add another account", wait=D_LONG):
          time.sleep(D_LONG)
          return
  ```

### Bẫy 2: Blind Tap tại `dismiss_profile_overlays` (`social_reg_v1.py`)
- **Hiện tượng:** Khi quét XML thấy `content-desc="Trang tính dưới cùng"` (vốn là container của mọi Bottom Sheet TikTok bao gồm cả Account Switcher), code thực hiện blind tap vào tọa độ cứng `(540, 1842)` rồi gửi `keyevent 4`.
- **Hậu quả:** Tọa độ `(540, 1842)` trên Samsung S7 nằm ngay vị trí nút Tạo video (+) / Camera ở thanh điều hướng đáy. Hành động này mở camera recording activity, sau đó gửi `keyevent 4` rồi lại lặp lại, dẫn đến treo vô hạn cho tới khi cạn timeout 180s.
- **Giải pháp:**
  - Loại trừ Account Switcher khỏi bộ lọc dismiss: `not _account_dropdown_open_xml(xml)`.
  - Triệt tiêu hoàn toàn blind tap `(540, 1842)`, chỉ tap nút đóng/hủy tường minh:
  ```python
  if (any(k in flat for k in ["dang ho tro:", "supporting:"]) or "fxs" in xml) and not _account_dropdown_open_xml(xml):
      log("   [profile] dismiss bottom sheet modal (fxs)")
      if not find_text_tap(device_id, "Hủy", "Huy", "Cancel", "Đóng", "Close", wait=D_SHORT):
          keyevent(device_id, 4, wait=D_SHORT)
      time.sleep(D_SHORT)
      continue
  ```

### Bẫy 3: Substring Matching nhầm Checkbox "đăng nhập" trên Màn hình 2FA Authenticator
- **Hiện tượng:** Khi nhập xong 6 số TOTP, hàm `tap_next` tìm các từ khóa `["Đăng nhập", "Dang nhap", "Log in", "Tiếp tục", "Continue"]`.
- **Hậu quả:** Trên màn hình 2FA có checkbox: *"Tin tưởng thiết bị này để bỏ qua xác minh 2 bước vào những lần **đăng nhập** sau."* Text này chứa substring `"đăng nhập"`. `find_text_tap` quét thấy chữ "đăng nhập" liền bấm vào checkbox thay vì bấm nút "Tiếp tục" ở đáy, khiến form không bao giờ được submit!
- **Giải pháp:**
  Trong `handle_tiktok_authenticator_2fa`, bấm tường minh nút `Tiếp tục` hoặc tọa độ nút submit `(540, 1683)`:
  ```python
  type_into_node(device_id, nodes[0], code, label="2fa", clear=True, sensitive=True)
  if not find_text_tap(device_id, "Tiếp tục", "Tiep tuc", "Continue", "Next", wait=D_LONG):
      tap(device_id, 540, 1683, wait=D_LONG)
  time.sleep(2.0)
  ```

### Bẫy 4: Lệch Giờ TOTP do Android 8 `date +%s` Không Hỗ Trợ
- **Hiện tượng:** `_device_epoch_seconds` gọi `adb shell date +%s`. Trên Samsung S7 Android 8, lệnh này trả về chuỗi rỗng (`""`), fallback hoặc đồng hồ máy bị lệch vài chục giây khiến mã TOTP 6 số bị TikTok từ chối liên tục 3 lần (`Ma 2FA khong qua sau 3 lan`).
- **Giải pháp:** Máy host PC Kibe đã đồng bộ NTP chuẩn xác tuyệt đối; dùng trực tiếp thời gian host `int(time.time())` để sinh mã TOTP:
  ```python
  def _device_epoch_seconds(device_id):
      return int(time.time())
  ```

### Bẫy 5: Khôi phục qua `--resume` Bỏ Qua Màn Nhập Email
- **Hiện tượng:** Nếu chạy `--resume` khi app đang ở `SignUpOrLoginActivity` (màn hình có `Email hoặc TikTok ID`), `resume_one_account` nhảy thẳng vào `drive_login_screens` (chỉ xử lý pass/2FA) mà không điền email, dẫn đến timeout 180s.
- **Giải pháp:** Trong `resume_one_account`, nếu phát hiện `is_auth_landing_screen(xml)` hoặc text `"email hoac tiktok id"`:
  ```python
  flat = strip_accents(xml).lower()
  if is_auth_landing_screen(xml) or any(k in flat for k in ["email hoac tiktok id", "nhap dia chi email", "email/ten nguoi dung"]):
      log("[resume-login] Phat hien man hinh nhap email / auth landing -> thuc hien chon email va nhap target")
      choose_email_login(device_id)
      login_target = (account.get("id") or "").strip() if (account.get("id") and account.get("tiktok_pass")) else account["login_email"]
      fill_existing_email_and_continue(device_id, login_target, stt=stt)
  ```

---

## 3. Quy luật Trần 8 Tài Khoản trên TikTok Switcher
- TikTok trên Android giới hạn tối đa đúng **8 tài khoản** đăng nhập đồng thời trên 1 thiết bị.
- Khi máy có 1..7 tài khoản: Slot cuối cùng luôn là nút **"Thêm tài khoản"** (`[0, 1788][1080, 1920]`).
- Khi máy đã đủ 8/8 tài khoản: Nút "Thêm tài khoản" **tự động biến mất**, danh sách hiển thị đầy đủ 8 account row.
- **Đường dẫn mở Switcher tin cậy 100%:** Khi các selector header / username trên Profile bị lệch, mở qua Settings:
  `Menu hồ sơ` (`[954, 96][1056, 204]`) -> `Cài đặt và quyền riêng tư` -> cuộn tìm `Chuyển đổi tài khoản`.

# Bẫy Substring Checkbox 2FA, Lệch Giờ TOTP NTP & Giới Hạn 8 Nick Switcher (2026-09-24)

## 1. Bối cảnh Sự cố (Ca nuôi Farm Kibe 14:00 - Máy 1)
- Ca nuôi feed bị dừng do thiếu nick thứ 4 (`ginnyhanstei80`), trong Switcher chỉ có 7 nick và nút *"Thêm tài khoản"*.
- Lệnh nạp bù tự động gọi `tiktok_login_v1.py` bị kẹt do 3 lỗi liên hoàn phát sinh trong quá trình xác thực 2FA và mở Switcher nghiệm thu.

---

## 2. Chi tiết Các Bẫy Kỹ Thuật & Giải Pháp Chuẩn

### Bẫy 1: Substring Matching Nhầm Checkbox "đăng nhập" trên Màn 2FA Authenticator
- **Triệu chứng:** Script đã gõ đúng 6 số TOTP vào ô `2fa field` nhưng không vượt qua được màn hình 2FA, lặp lại 3 lần rồi báo `[2fa-app] Ma 2FA khong qua sau 3 lan`.
- **Root cause:**
  - Hàm `tap_next` tìm các từ khóa: `["Đăng nhập", "Dang nhap", "Log in", "Tiếp tục", "Continue"]`.
  - Trên màn 2FA có checkbox: *"Tin tưởng thiết bị này để bỏ qua xác minh 2 bước vào những lần **đăng nhập** sau."*
  - Do cơ chế tìm kiếm text lỏng lẻo (`strip_accents`), từ khóa `"đăng nhập"` đã khớp vào chuỗi của checkbox!
  - Thay vì bấm nút "Tiếp tục" ở đáy màn hình (`bounds=[455, 1658][625, 1708]`), script liên tục tap vào checkbox `(576, 1480)`, khiến form 2FA không bao giờ được gửi đi!
- **Fix triệt để (`social_reg_v1.py`):**
  Trong `handle_tiktok_authenticator_2fa`, bấm tường minh nút `Tiếp tục` / `Continue` hoặc tap tọa độ submit `(540, 1683)`:
  ```python
  type_into_node(device_id, nodes[0], code, label="2fa", clear=True, sensitive=True)
  if not find_text_tap(device_id, "Tiếp tục", "Tiep tuc", "Continue", "Next", wait=D_LONG):
      tap(device_id, 540, 1683, wait=D_LONG)
  time.sleep(2.0)
  ```

### Bẫy 2: Lệch Giờ TOTP do Android 8 `date +%s` Không Hỗ Trợ
- **Triệu chứng:** Mã 2FA sinh ra bị TikTok từ chối liên tục dù secret TOTP trong Excel/tracking là hoàn toàn chính xác.
- **Root cause:**
  - `_device_epoch_seconds` gọi `adb shell date +%s`.
  - Trên Android 8 (Samsung S7), toolbox `date` không hỗ trợ format `+%s` và trả về chuỗi rỗng `""`.
  - Đồng hồ thiết bị có thể trôi lệch so với thời gian thực tế vài chục giây, khiến mã TOTP 30s bị lệch chu kỳ.
- **Fix triệt để (`social_reg_v1.py`):**
  Máy tính chủ (Host PC Kibe) luôn được đồng bộ NTP chuẩn xác tuyệt đối; dùng trực tiếp `int(time.time())`:
  ```python
  def _device_epoch_seconds(device_id):
      # Host time is NTP-synchronized; Android S7 device clock drifts causing TOTP failures
      return int(time.time())
  ```

### Bẫy 3: `--resume` Không Nhận Diện Màn Nhập Email
- **Triệu chứng:** Khi app đang ở `SignUpOrLoginActivity` (màn hình có `Email hoặc TikTok ID`), chạy cờ `--resume` nhảy thẳng vào `drive_login_screens` (chỉ xử lý pass/2FA) mà không điền email, dẫn đến timeout 180s.
- **Fix triệt để (`tiktok_login_v1.py`):**
  Trong `resume_one_account`, nếu phát hiện `is_auth_landing_screen(xml)` hoặc text `"email hoac tiktok id"`:
  ```python
  flat = strip_accents(xml).lower()
  if is_auth_landing_screen(xml) or any(k in flat for k in ["email hoac tiktok id", "nhap dia chi email", "email/ten nguoi dung"]):
      log("[resume-login] Phat hien man hinh nhap email / auth landing -> thuc hien chon email va nhap target")
      choose_email_login(device_id)
      login_target = (account.get("id") or "").strip() if (account.get("id") and account.get("tiktok_pass")) else account["login_email"]
      fill_existing_email_and_continue(device_id, login_target, stt=stt)
  ```

### Bẫy 4: Mở Account Switcher trên Profile Layout Mới
- **Triệu chứng:** Tap vào Display Name `(300, 322)` hoặc `@handle` không mở được Switcher, vuốt lên cũng không hiện sticky header.
- **Fix chuẩn 100%:** Fallback mở qua Cài đặt:
  `Menu hồ sơ` (`[954, 96][1056, 204]`) -> `Cài đặt và quyền riêng tư` -> Cuộn tìm `Chuyển đổi tài khoản`.

---

## 3. Quy Luật Trần 8 Tài Khoản trên TikTok Android
- TikTok Android giới hạn cứng tối đa đúng **8 tài khoản** đăng nhập đồng thời.
- **Khi máy có 1..7 nick:** Vị trí cuối cùng trong danh sách Switcher luôn là nút *"Thêm tài khoản"*.
- **Khi máy đã đủ 8 nick:** Nút *"Thêm tài khoản"* **tự động biến mất**, nhường chỗ cho toàn bộ 8 tài khoản.
- **Giao tiếp User:** Khi User thắc mắc *"ủa vẫn chỉ có 7 nick mà"*, cần kiểm tra thời gian của ảnh. Nếu đó là ảnh cũ lúc dừng ca (14:16) thì máy đang thiếu nick thật. Sau khi chạy nạp bù thành công, phải chụp ảnh Switcher mới (20:55) hiển thị đầy đủ 8/8 nick để nghiệm thu.

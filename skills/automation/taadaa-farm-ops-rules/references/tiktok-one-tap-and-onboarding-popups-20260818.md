# TikTok One-Tap Login, Onboarding Popups & Quick Account Switcher (2026-08-18)

## 1. Màn hình One-tap Login / Quick Login ("Tiếp tục với tên @username")
- **Hiện tượng**: Khi vào flow đăng ký tài khoản TikTok mới (sau khi tap *Thêm tài khoản* hoặc mở app), TikTok nhận diện trên máy đã từng có tài khoản trước đó và hiển thị màn hình gợi ý đăng nhập nhanh:
  - Nút đỏ lớn ở giữa: *"Tiếp tục với tên @username"*
  - Footer ở dưới cùng: Dòng liên kết text màu xám: **"Sử dụng tài khoản khác"** (hoặc "Use another account").
- **Lỗi phát sinh cũ**: Script tìm ngay các marker của màn hình chọn phương thức (*"Dùng số điện thoại / Email"*) $\rightarrow$ không thấy $\rightarrow$ Báo lỗi `[06] Không thấy màn chọn phương thức đăng nhập` hoặc `[06_email_option]`.
- **Cách xử lý chuẩn (đã verify live)**:
  - Kiểm tra nếu `initial_flat` có chứa `"tiep tuc voi ten"` hoặc `"su dung tai khoan khac"`:
  ```python
  if "tiep tuc voi ten" in initial_flat or "su dung tai khoan khac" in initial_flat:
      log("   [6] Màn Đăng nhập nhanh -> tap 'Sử dụng tài khoản khác'")
      find_text_tap(device_id, "Sử dụng tài khoản khác", "Su dung tai khoan khac", "Use another account", wait=D_SHORT)
      time.sleep(1.5)
      initial_xml = get_ui_xml(device_id)
      initial_flat = strip_accents(initial_xml).lower()
  ```
  - Sau khi tap *"Sử dụng tài khoản khác"*, TikTok sẽ mở ra danh sách đầy đủ các phương thức đăng nhập/đăng ký.

---

## 2. Popup Điều khoản Onboarding ("Đồng ý và tiếp tục")
- **Hiện tượng**: Khi khởi động app TikTok trên thiết bị mới / cache reset, một modal popup màu trắng xuất hiện ở giữa màn hình:
  - Nội dung: *"Bằng cách nhấn vào "Đồng ý và tiếp tục", bạn đồng ý với Điều khoản Dịch vụ..."*
  - Nút bấm: **"Đồng ý và tiếp tục"** (hoặc "Agree and continue").
- **Cách xử lý trong `_dismiss_system_popups`**:
  ```python
  if "dong y va tiep tuc" in flat or "agree and continue" in flat:
      log("   [popup] Bấm 'Đồng ý và tiếp tục' popup điều khoản")
      find_text_tap(device_id, "Đồng ý và tiếp tục", "Dong y va tiep tuc", "Agree and continue", wait=D_SHORT)
      time.sleep(1.0)
      xml = get_ui_xml(device_id)
  ```

---

## 3. ATX-Agent Primary UI Capture — Tuyệt đối không dùng Shell UIAutomator trực tiếp
- User nhắc lại (18/08): Toàn bộ farm Taadaa sử dụng **ATX-Agent (TCP port 7912)** quản lý bởi `automation-core` làm cơ chế đọc UI duy nhất và ưu tiên số 1.
- Nếu gặp lỗi `UI_XML_TIMEOUT` từ shell fallback $\rightarrow$ đó là triệu chứng của việc ATX-Agent hoặc stub `com.github.uiautomator` trên máy bị crash/treo.
- **Khôi phục**:
  - Chạy `adb shell "monkey -p com.github.uiautomator 1"` để hồi sinh stub.
  - Chạy `adb shell "/data/local/tmp/atx-agent server -d"` để đảm bảo daemon port 7912 lắng nghe.

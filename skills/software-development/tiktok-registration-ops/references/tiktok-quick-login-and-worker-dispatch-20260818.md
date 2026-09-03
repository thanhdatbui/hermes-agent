# TikTok One-Tap Quick Login Screen Resolution & Child Worker Dispatch (18/08/2026)

## 1. Màn hình Gợi ý Đăng nhập nhanh ("Tiếp tục với tên @username")
- **Hiện tượng**: Sau khi bấm "Thêm tài khoản" ở account switcher, TikTok không vào thẳng màn chọn phương thức mà hiển thị giao diện One-tap Login với nút đỏ lớn *"Tiếp tục với tên @username"* và dòng liên kết xám *"Sử dụng tài khoản khác"* ở dưới cùng.
- **Xử lý**: 
  - Thêm check trong `choose_email_login`:
  ```python
  if "tiep tuc voi ten" in initial_flat or "su dung tai khoan khac" in initial_flat:
      log("   [6] Màn Đăng nhập nhanh -> tap 'Sử dụng tài khoản khác'")
      find_text_tap(device_id, "Sử dụng tài khoản khác", "Su dung tai khoan khac", "Use another account", wait=D_SHORT)
      time.sleep(1.5)
      initial_xml = get_ui_xml(device_id)
      initial_flat = strip_accents(initial_xml).lower()
  ```
  - Thao tác này mở ra đúng danh sách phương thức đăng nhập ("Dùng số điện thoại / Email").

## 2. Dispatch Worker STT Fix trong `_run_all_targets.py`
- Hàm `build_child_command` phải truyền `str(target["stt"])` thay vì `target.get("stt", "")` để đảm bảo worker nhận đúng định dạng số máy nguyên.

## 3. Duy trì ATX-Agent Primary
- Khi gặp `UI_XML_TIMEOUT` ở shell uiautomator fallback, restart ATX-Agent:
  ```bash
  adb -s <serial> shell '/data/local/tmp/atx-agent server -d'
  adb -s <serial> shell 'monkey -p com.github.uiautomator 1'
  ```

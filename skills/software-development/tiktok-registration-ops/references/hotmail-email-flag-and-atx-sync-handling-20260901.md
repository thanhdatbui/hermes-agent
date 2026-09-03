# Hotmail Target Forwarding, ATX Synchronized Recovery & Gmail Sync Bypass (2026-09-01)

## 1. Hotmail/Outlook Explicit Target Forwarding (`--email`)
- **Hiện tượng**: `_detect_clean.py` phân loại target máy sử dụng provider `hotmail` (đọc OTP qua Outlook app hoặc Microsoft Graph API), nhưng `_run_all_targets.py` không truyền tham số `--email <target_email>` khi fork tiến trình con `social_reg_v1.py`.
- **Hệ quả**: Tiến trình con không biết target mail được cấp phát, tự động fallback đọc lại `gmail_clean_v2.xlsx` và bốc trúng các Gmail cũ (vốn không có trên thiết bị). Tiến trình mở app Gmail để tìm OTP nhưng thất bại, báo lỗi sai lệch dù Hotmail Graph Token hoàn toàn hợp lệ.
- **Giải pháp**:
  - `_run_all_targets.py` bắt buộc truyền cờ `--email <email>` vào `build_child_command` khi target có trường email.
  - `social_reg_v1.py` nhận cờ `--email` / biến môi trường `SOCIAL_PREFERRED_EMAIL`, ưu tiên sử dụng email được truyền xuống trước khi quét workbook fallback.

## 2. Đồng bộ cơ chế ATX Primary & Auto-Recovery (`get_ui_xml`)
- **Hiện tượng**: `get_ui_xml` trong `social_reg_v1.py` đặt tổng thời gian timeout quá ngắn (`UI_XML_TOTAL_TIMEOUT = 35s`) và `cap=8s`. Khi ATX stub bị treo, 3 lần retry đầu tiên ngốn hết thời gian khiến hàm timeout ngay mà không kịp thực hiện `reset_atx_agent()`.
- **Hệ quả**: Tiến trình fail-closed sớm với lỗi `[adb-timeout] UI_XML_TIMEOUT device=... detail=atx-exhausted` dù máy vẫn online. Khi stub treo, `ADB_KEYBOARD_INPUT_TEXT` cũng không gõ được text vào ô email/password, khiến nút "Tiếp tục" bị vô hiệu hóa.
- **Giải pháp chuẩn (đồng bộ từ `tiktok-luot nuoi acc` / `automation-core`)**:
  ```python
  def get_ui_xml(device_id, deadline=None):
      started = time.monotonic()
      local_deadline = started + 60.0
      if deadline is not None:
          local_deadline = min(local_deadline, deadline)

      # 1. Thử ATX session 3 lần với timeout 15s
      for attempt in range(1, 4):
          rem = local_deadline - time.monotonic()
          if rem <= 1.0:
              break
          atx_xml = _atx_capture_ui_xml(device_id, timeout=min(15.0, rem), restart_attempts=0)
          if atx_xml and "<hierarchy" in atx_xml:
              return atx_xml
          time.sleep(0.5)

      # 2. Hard reset ATX agent + stub nếu 3 lần fail
      rem = local_deadline - time.monotonic()
      if rem > 2.0:
          try:
              from automation_core.adb import AdbClient
              from automation_core.persistent_ui import reset_atx_agent
              client = AdbClient(adb_path=ADB_PATH, serial=device_id, default_timeout=20)
              reset_atx_agent(client, timeout=min(15.0, rem))

              # 3. Retry sau reset 2 lần
              for post_attempt in range(1, 3):
                  rem_post = local_deadline - time.monotonic()
                  if rem_post <= 1.0:
                      break
                  atx_xml = _atx_capture_ui_xml(device_id, timeout=min(15.0, rem_post), restart_attempts=1)
                  if atx_xml and "<hierarchy" in atx_xml:
                      return atx_xml
                  time.sleep(0.5)
          except Exception as exc:
              log(f"   [ui-xml] atx reset failed: {exc}")

      return ""
  ```

## 3. Popup Google Sync & Account Switcher Dropdown IDs
- **Gmail Sync Dialog**: Dialog *"Bật tính năng tự động đồng bộ hóa?"* của Gmail mang resource ID `com.google.android.gm:id/alertTitle` (hoặc `android:id/alertTitle`). Bộ lọc dialog popup phải kiểm tra regex `alertTitle|alert_title` hoặc text `đồng bộ hóa|sync` để tự động bấm nút Xác nhận / OK.
- **TikTok Account Dropdown Switcher**: Trên các bản build TikTok mới, dropdown switch account tại profile root bổ sung thêm resource ID `pkh`, `pke` bên cạnh `rv5`, `sticky_header` và `sv6`.

# Device Screen Timeout & Stay-On Policy (Farm Standard)

## Context
Trên farm Android (đặc biệt các thiết bị cắm sạc liên tục như Samsung Galaxy SM-G930F/W8 hoặc các máy chạy runner `tiktok-luot nuoi acc`), việc để màn hình luôn sáng (`stayon true` / `stay_on_while_plugged_in 7` / timeout 30 phút `1800000ms`) làm nóng máy, hao pin, phồng pin và giảm tuổi thọ màn hình OLED (burn-in).

## Chuẩn cấu hình màn hình trong `device_prepare.py`
Trong `python_runner/flows/device_prepare.py` -> `configure_device_screen_stay_on(ctx)`:
- **Tắt ép sáng khi cắm sạc**:
  ```python
  ["svc", "power", "stayon", "false"]
  ["settings", "put", "global", "stay_on_while_plugged_in", "0"]
  ```
- **Thời gian chờ tắt màn hình (Screen Off Timeout)**: 10 phút (600,000 ms)
  ```python
  ["settings", "put", "system", "screen_off_timeout", "600000"]
  ```
- **Giữ bypass / vô hiệu hóa lockscreen** để adb có thể tự động bật/tắt hoặc tương tác không bị khóa mật khẩu:
  ```python
  ["settings", "put", "secure", "lockscreen.disabled", "1"]
  ["settings", "put", "secure", "lock_screen_lock_after_timeout", "2147483647"]
  ["locksettings", "set-disabled", "true"]
  ```

## Pitfalls khi kiểm thử bằng script ad-hoc
- Khi viết script verify bằng Python tạm thời trên Windows (`tempfile.NamedTemporaryFile`), chuỗi đường dẫn Windows như `D:\Taadaa\tiktok-luot nuoi acc\...` chứa escape sequence (như `\t`, `\f`) gây `OSError: [Errno 22] Invalid argument` nếu không escape thành `D:\\...` hoặc dùng raw string trong code được sinh ra.

# Force Portrait Lock & Auto-Rotate Prevention on Samsung Android Farm

## 1. Nguyên nhân lỗi xoay ngang (Root Cause)
Trên các máy Samsung Galaxy (S7 SM-G930F / SM-G930W8):
* Lệnh `settings put system accelerometer_rotation 0` chỉ tắt tính năng tự động xoay trong Settings.
* Khi mở bàn phím (IME), WebView hoặc các ứng dụng có orientation cấu hình rộng (Outlook, Gmail), hệ thống Android có thể tự động switch sang chế độ Landscape (`mCurrentRotation=1`), khiến toàn bộ tọa độ và layout bị lệch.
* Lệnh `wm user-rotation lock 0` trên một số bản ROM Samsung cũ sẽ báo lỗi `Error: unknown command 'user-rotation'`.

## 2. Giải pháp khóa dọc cứng chuẩn xác (Canonical Fix)
Cần kết hợp trực tiếp cập nhật `settings/system` qua cả `settings put` và `content insert`:

```bash
# 1. Tắt accelerometer rotation
adb shell settings put system accelerometer_rotation 0
adb shell content insert --uri content://settings/system --bind name:s:accelerometer_rotation --bind value:i:0

# 2. Ép hướng xoay của người dùng về 0 (Portrait)
adb shell settings put system user_rotation 0
adb shell content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:0
```

Trong Python:
```python
def ensure_portrait_mode(adb: str, serial: str) -> None:
    """Ensure device is strictly in portrait mode and auto-rotate is disabled."""
    subprocess.run([adb, "-s", serial, "shell", "settings", "put", "system", "accelerometer_rotation", "0"], capture_output=True)
    subprocess.run([adb, "-s", serial, "shell", "settings", "put", "system", "user_rotation", "0"], capture_output=True)
    subprocess.run([adb, "-s", serial, "shell", "content", "insert", "--uri", "content://settings/system", "--bind", "name:s:accelerometer_rotation", "--bind", "value:i:0"], capture_output=True)
    subprocess.run([adb, "-s", serial, "shell", "content", "insert", "--uri", "content://settings/system", "--bind", "name:s:user_rotation", "--bind", "value:i:0"], capture_output=True)
```

## 3. Xác thực sau khi áp dụng (Verification)
Kiểm tra biến `mCurrentRotation` qua WindowManager:
```bash
adb shell dumpsys window | grep mCurrentRotation
# Kết quả hợp lệ: mCurrentRotation=0 (Portrait)
```

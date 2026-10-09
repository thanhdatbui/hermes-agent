# Quy chuẩn ADB Device Validation & Backoff (`multi_machine_feed_session.py`)

## Bối cảnh
Khi chạy multi-machine feed runner trên nhiều máy đồng thời, server ADB có thể quá tải đột ngột dẫn đến việc thiết bị tạm thời không phản hồi lệnh `adb devices` hoặc quăng `ADBError`. Thiết lập trước đây (`ADB_ONLINE_ATTEMPTS = 2` với fixed sleep 1.0s) dễ gây rớt máy thành `config-error` dù máy vẫn online.

## Patch Contract chuẩn
Trong file `python_runner/flows/multi_machine_feed_session.py`:

1. **Hằng số số lần thử:**
   ```python
   ADB_ONLINE_ATTEMPTS = 5  # nâng từ 2 lên 5
   ```

2. **Cơ chế Backoff lũy tiến:**
   - Trong khối `except ADBError`:
     ```python
     except ADBError as exc:
         last_error = str(exc)
         if _attempt < ADB_ONLINE_ATTEMPTS:
             time.sleep(1.0 * _attempt)
         continue
     ```
   - Trong khối thiết bị chưa có trong danh sách devices:
     ```python
     last_error = f"Device serial {mask_value(serial, prefix='device')!r} was not found in adb devices."
     if _attempt < ADB_ONLINE_ATTEMPTS:
         time.sleep(1.0 + 0.5 * _attempt)
     ```

## Lưu ý đường dẫn trên Windows Git Bash
- Khi chạy git lệnh hoặc kiểm tra repo với đường dẫn có dấu cách như `D:\Taadaa\tiktok-luot nuoi acc`:
  - Tránh dùng `/d/Taadaa/...` nếu MSYS không mount `/d`. Dùng định dạng `D:/Taadaa/tiktok-luot nuoi acc` bọc trong dấu ngoặc kép.

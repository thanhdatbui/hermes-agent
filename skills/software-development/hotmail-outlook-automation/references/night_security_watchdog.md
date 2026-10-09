# Night Hotmail Security Watchdog

File: `D:\Taadaa\Hotmail\scripts\cron_night_hotmail_security_watchdog.py`

## Mục đích & Cơ chế hoạt động
- Tự động quét các tài khoản Hotmail ngâm đủ ngày (`MIN_AGE_DAYS = 7`), chưa đổi pass (`info_changed != 1`) và không dính khoalee để đổi mật khẩu và gỡ mail khôi phục trong khung giờ đêm.
- Xử lý qua lock thiết bị ADB để tránh xung đột với các batch job khác.

## Quy chuẩn Telegram Farm Alert
- Khi kết thúc một tick chạy, script chỉ in thông báo ra stdout khi `processed_count > 0` nhằm tránh spam alert tới Telegram Farm Alert khi không có tài khoản nào được xử lý:
  ```python
  if processed_count > 0:
      print(f"[BẢO MẬT HOTMAIL ĐÊM] ✓ Đã đổi pass + gỡ mail khôi phục thành công {processed_count} acc (ngâm >= {MIN_AGE_DAYS} ngày)")
  ```
- Khi `processed_count == 0`: Hoàn toàn im lặng trên stdout (vẫn ghi log debug bình thường).

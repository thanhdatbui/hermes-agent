# Samsung S7 Permanent MTP USB Popup Disable via Package Manager (2026-09-20)

## Triệu chứng & Nguyên nhân
- Trên các dòng máy Samsung Galaxy S7 (Android 7/8), khi cắm cáp USB, điện áp USB hub chập chờn hoặc thiết bị khởi động lại, dịch vụ `MtpApplication` tự động bật popup cảnh báo:
  `com.samsung.android.MtpApplication/.USBConnection`
  *"Chú ý: Thiết bị được kết nối không thể truy cập dữ liệu trên thiết bị này..."*.
- Popup này cướp foreground, chặn các thao tác UIAutomator/ATX và làm gián đoạn ADB bridge, gây ra các lỗi `[adb-timeout] device=<serial> timeout=20`.

## Giải pháp Triệt để (Vô hiệu hóa vĩnh viễn)
- Không cần tap "OK" hay "Hủy" tạm thời mỗi lần cắm cáp. Thực hiện vô hiệu hóa gói ứng dụng hệ thống trên user 0 bằng lệnh ADB:
  ```bash
  adb -s <serial> shell pm disable-user --user 0 com.samsung.android.MtpApplication
  ```
- Kết quả xác nhận: `Package com.samsung.android.MtpApplication new state: disabled-user`.
- Sau khi disable, popup MTP USB sẽ biến mất vĩnh viễn và không bao giờ tự bung lại khi cắm/rút cáp hay khởi động lại thiết bị.

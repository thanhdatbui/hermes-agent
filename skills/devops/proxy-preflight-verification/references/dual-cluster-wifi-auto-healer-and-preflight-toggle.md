# Dual-Cluster Wi-Fi Auto-Healing & Preflight Radio Toggle Architecture

## 1. Cạm Bẫy `svc wifi enable` Đơn Thuần Trong Preflight
- **Hiện tượng**: Trên thiết bị Android (đặc biệt dòng Samsung Galaxy S7 Android 7/8), khi máy bị rớt AP do nhiễu sóng RF, AP tái khởi động hoặc kẹt lease DHCP, công tắc Wi-Fi trong Cài đặt hệ thống thực tế vẫn đang ở trạng thái ON.
- **Hạn chế**: Lệnh `svc wifi enable` đơn thuần trong runner (`vpn_preflight.py`) không có tác dụng tái kích hoạt vì hệ điều hành coi Wi-Fi đã bật. Kết quả là lượt probe kế tiếp tiếp tục báo `dumpsys connectivity: Wi-Fi not connected` và kích hoạt kill-switch ngắt phiên (`blocked-proxy-vpn`).
- **Giải Pháp Chuẩn**: Bắt buộc thực hiện chu kỳ toggle đầy đủ:
  ```python
  adb.shell(["svc", "wifi", "disable"], timeout=5, check=False)
  time.sleep(1.0)
  adb.shell(["svc", "wifi", "enable"], timeout=5, check=False)
  time.sleep(3.0)  # chờ radio quét và gán lại IP
  ```

## 2. Quy Tắc Parity 2 Cụm (Dual-Cluster Parity) Cho Watchdog Phục Hồi
- Farm Taadaa vận hành song song 2 cụm:
  - **Cụm 1 (Kibe Local)**: Máy 1–80, kết nối trực tiếp qua USB bus host cá nhân. Cấu hình đọc từ `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`.
  - **Cụm 2 (Admin Remote)**: Máy 201–280, kết nối qua mạng nội bộ ADB port proxy `192.168.110.119:5037`. Cấu hình đọc từ `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx`.
- **Cạm bẫy cục bộ**: Watchdog tự động khôi phục mạng (`farm_wifi_auto_healer.py`) nếu chỉ chạy `adb devices` mặc định sẽ chỉ cứu được cụm Kibe và bỏ sót hoàn toàn 80 máy Admin.
- **Quy tắc thiết kế Watchdog**:
  - Phải lặp qua cả 2 endpoint: `[ADB_BIN]` và `[ADB_BIN, "-H", "192.168.110.119", "-P", "5037"]`.
  - Kiểm tra interface `wlan0`: Nếu không tìm thấy IP `192.168.x.x` -> Tự động toggle Wi-Fi radio (`svc wifi disable && sleep 1 && svc wifi enable`).
  - Giữ nguyên triết lý Silent Watchdog: Chỉ in thông báo khi có ít nhất 1 máy được cứu thành công; im lặng tuyệt đối khi toàn bộ máy đã có kết nối ổn định.

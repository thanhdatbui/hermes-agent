# Chẩn Đoán Phân Biệt Mất Kết Nối ADB/USB vs Wi-Fi (AP) & Bẫy Crash Android Settings Service

## 1. Bản Chất Sự Cố (22/10/2026)
- **Hiểu lầm phổ biến của vận hành:** Thấy báo cáo Watchdog ghi *"Mất kết nối"* thì thắc mắc *"tại sao có cron ép connect Wi-Fi rồi mà máy vẫn mất kết nối?"*.
- **Nguyên lý cốt lõi:**
  1. Mọi cron quản trị Wi-Fi (`adb-join-wifi`, check SSID, set proxy) đều chạy từ Host PC (Kibe/Admin) và **bắt buộc phải truyền lệnh qua cáp USB thông qua ADB daemon (`adb shell`)**.
  2. Khi máy bị **"Mất kết nối ADB/USB"** (`device not found` hoặc `offline`): Tầng transport USB bị đứt hoặc daemon ADB mất liên lạc. Host PC hoàn toàn mất kênh điều khiển, không thể gửi bất kỳ lệnh shell nào vào máy (cả lệnh ép Wi-Fi lẫn thao tác app).
  3. Vì vậy: Cron ép Wi-Fi CHỈ có tác dụng khi ADB/USB còn sống (`device`). Khi cáp USB lỏng hoặc bus EHCI kẹt, cron Wi-Fi bất khả thi.

## 2. Bẫy False-Positive: "Mất kết nối Wi-Fi (AP)" Do Crash `system_server` (`cmd: Can't find service: settings`)
- **Hiện tượng thực tế (Máy 213 - Admin Farm):**
  - Watchdog báo: `Fail: M213 - Mất kết nối Wi-Fi (AP)`.
  - Kiểm tra thực tế qua `inspect_machine.py 213`:
    * `Wi-Fi IP: 192.168.110.87` (Đã nhận IP hợp lệ từ DHCP MikroTik!).
    * `Proxy: cmd: Can't find service: settings`.
    * `Current Focus: None`.
- **Bản chất kỹ thuật:**
  - Máy KHÔNG HỀ mất Wi-Fi. Wi-Fi vẫn kết nối và có IP LAN.
  - Tuy nhiên, tiến trình cốt lõi `system_server` hoặc `settings provider` trong Android của Samsung S7 bị deadlock hoặc crash ngầm.
  - Khi runner chạy lệnh `settings get global http_proxy`, Android trả về `cmd: Can't find service: settings`.
  - Runner/Watchdog bắt lỗi này và phân loại nhầm thành "Mất kết nối Wi-Fi (AP)" do không đọc được proxy.

## 3. Quy Trình Cứu Hộ O(1) Bằng `recover_stuck_s7.py`
- Khi gặp `Can't find service: settings`, các lệnh Level 1 soft recovery (`am force-stop`, `input keyevent`) sẽ thất bại vì shell service không phản hồi.
- Script chuẩn hóa `D:/Taadaa/tools/recover_stuck_s7.py -m <N>` tự động phát hiện và leo thang:
  ```bash
  python D:/Taadaa/tools/recover_stuck_s7.py -m 213
  ```
  1. *Level 1 Soft Recovery:* Thất bại trong 0.2s do shell treo.
  2. *Level 2 Direct Reboot:* Tự động kích hoạt `adb -s <serial> reboot` (gửi signal trực tiếp tới service `reboot:` của daemon `adbd`, bypass hoàn toàn `/system/bin/sh` và `system_server` đang đơ).
  3. Sau 20-30s khởi động lại, `system_server` tái tạo sạch sẽ:
     - Nhận lại đầy đủ Wi-Fi IP (`192.168.110.80`).
     - Proxy nhận chuẩn (`192.168.110.2:10012`).
     - Launcher focus phục hồi, máy sẵn sàng vào ca chạy tiếp theo.

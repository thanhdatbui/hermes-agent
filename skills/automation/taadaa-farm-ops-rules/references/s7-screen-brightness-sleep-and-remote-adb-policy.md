# Farm S7 Screen Power, Brightness, and Auto Sleep Policy

## 1. Nguyên lý hoạt động Màn hình Farm S7
- **Khi đang chạy task (Active Run):** Các thao tác ADB (`tap`, `swipe`, `uiautomator dump`, `screencap`) liên tục gửi tín hiệu tương tác người dùng, tự động reset bộ đếm thời gian chờ của Android. Do đó, màn hình máy **giữ sáng liên tục trong suốt ca chạy**, đảm bảo tool view màn hình (AnLink / tool con gấu, Scrcpy) vẫn hiển thị và điều khiển bình thường.
- **Khi nghỉ / xong ca (Idle):** Sau khi kết thúc task và về HOME, không còn tương tác ADB, sau đúng **10 phút** (`screen_off_timeout 600000`), màn hình thiết bị sẽ **tự động tắt ngúm (Sleep)** để hạ nhiệt phần cứng và tiết kiệm điện.
- **Độ sáng màn hình vật lý (Physical Screen Brightness):**
  - Hạ độ sáng về 0 (`settings put system screen_brightness 0`, `screen_brightness_mode 0`) chỉ làm tối đèn nền vật lý ngoài đời thực để chống nóng và chống cháy/ám tấm nền AMOLED S7.
  - **Tool AnLink / Scrcpy đọc trực tiếp từ Framebuffer/GPU qua USB**, do đó trên máy tính vẫn nhìn thấy rõ ràng 100% không bị ảnh hưởng bởi độ sáng màn hình vật lý.

## 2. Invariant Script Runner (CẤM ÉP SÁNG VĨNH VIỄN)
- **CẤM TUYỆT ĐỐI** nhồi các lệnh sau vào script chuẩn bị thiết bị (`prepare_device`):
  - `svc power stayon true` -> BẮT BUỘC: `svc power stayon false`
  - `settings put global stay_on_while_plugged_in 7` -> BẮT BUỘC: `settings put global stay_on_while_plugged_in 0`
  - `settings put system screen_off_timeout 1800000` (30p) -> BẮT BUỘC: `settings put system screen_off_timeout 600000` (10 phút)
- Các file quản lý cấu hình màn hình:
  - Core chung: `D:/Taadaa/automation-core/src/automation_core/device.py` (hàm `configure_stay_on`)
  - Feed nuốt acc: `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/device_prepare.py` (hàm `configure_device_screen_stay_on`)

## 3. Remote ADB Auto-Startup qua Mạng LAN (Admin ↔ Kibe)
- Khi kết nối liên máy giữa Master (Kibe) và Worker (Admin) qua ADB LAN (port `5037`):
  - Không chạy file `.bat` thủ công vì sẽ mất kết nối khi máy Admin khởi động lại.
  - Cài đặt dịch vụ tự động vĩnh viễn qua Windows Task Scheduler (`schtasks`) với trigger `onstart` (SYSTEM) và `onlogon` với quyền `HIGHEST`.
  - Mở Windows Firewall rule TCP Inbound port 5037:
    ```cmd
    netsh advfirewall firewall add rule name="ADB Remote 5037" dir=in action=allow protocol=TCP localport=5037
    ```
  - Khởi chạy tiến trình nền: `adb -a nodaemon server`.

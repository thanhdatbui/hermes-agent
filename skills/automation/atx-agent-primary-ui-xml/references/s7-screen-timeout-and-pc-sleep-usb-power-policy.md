# S7 Screen Timeout & PC USB Power Management Policy (2026-09-16)

## 1. Hiện tượng & Vấn đề thực tế
- Khi máy PC (Kibe) sleep hoặc ngắt/nối lại phiên RDP/USB bus, toàn bộ dàn S7 bị hiện lại popup xác thực RSA ADB dù trước đó đã bấm "Luôn cho phép".
- Dàn S7 bị sáng màn hình liên tục không tự tắt (hoặc set lại tắt màn hình rồi một thời gian sau lại bị sáng vô tận), gây nóng máy, chai pin và phồng pin trong box.

## 2. Root Cause Analysis
1. **Windows USB Root Hub Power Management (PC-side)**:
   - Windows 10 bật mặc định tính năng "Allow the computer to turn off this device to save power" trên `USB Root Hub (USB 3.0)` (`USB\ROOT_HUB30\5&f8bad21&0&0_0`).
   - Khi PC idle hoặc sleep (S3 Standby), Windows ngắt nguồn USB Host Controller làm 80 máy ngắt kết nối đồng loạt. Khi wake up, 80 máy cùng handshake ADB một lúc gây broken pipe/race condition khiến tiến trình adbd fallback hiện popup RSA.
   - **Xử lý trên PC**:
     ```powershell
     $t = Get-CimInstance MSPower_DeviceEnable -Namespace root\wmi | Where-Object { $_.InstanceName -like '*USB\ROOT_HUB30*' }
     $t.Enable = $false
     Set-CimInstance -CimInstance $t
     ```
     Đồng thời tắt sleep trên PC farm:
     ```cmd
     powercfg /change standby-timeout-ac 0
     powercfg /change hibernate-timeout-ac 0
     ```

2. **`atx-agent` ép sáng màn hình vô tận (`2147483647` ms)**:
   - Daemon `atx-agent server -d` khi khởi động mặc định gọi Android API set `screen_off_timeout = Integer.MAX_VALUE` (`2147483647` ms = 24.8 ngày).
   - Mỗi lần USB reset hoặc runner phục hồi/restart ATX agent, toàn bộ dàn máy bị ghi đè thành không bao giờ tắt màn hình.
   - **Xử lý trong codebase (`automation-core`)**:
     - BẮT BUỘC khởi chạy `atx-agent` với cờ `--nouia`:
       ```python
       started = adb.shell([ATX_AGENT_PATH, "server", "-d", "--nouia"], timeout=timeout, check=False)
       ```
       (Áp dụng trong `persistent_ui.py` tại `capture_persistent_ui`, `_ensure_atx_server_running`, và `reset_atx_agent`).
     - Kích hoạt stub nền riêng qua HTTP endpoint mà không làm đổi timeout:
       ```bash
       /data/local/tmp/atx-agent curl -X POST http://127.0.0.1:7912/uiautomator
       ```
     - Cập nhật unit test assertions trong `tests/test_persistent_ui.py`:
       `call[-3:] == ["server", "-d", "--nouia"]` và `call[-4:] == [persistent_ui.ATX_AGENT_PATH, "server", "-d", "--nouia"]`.

3. **Cấu hình chuẩn đồng bộ cho S7 Farm**:
   ```bash
   settings put system screen_off_timeout 600000     # 10 phút (600.000 ms)
   settings put global stay_on_while_plugged_in 0    # Không giữ sáng khi cắm sạc
   svc power stayon false                            # Tắt stayon service
   ```

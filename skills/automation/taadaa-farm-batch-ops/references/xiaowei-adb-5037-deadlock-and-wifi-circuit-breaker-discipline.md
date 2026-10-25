# Xử Lý Kẹt ADB Tiểu Vi Port 5037 & Kỷ Luật Circuit Breaker Cho Wi-Fi Auto-Healer

## 1. Sự Cố Xung Đột ADB Tiểu Vi: Port 5037 vs Port 5038

### Bối Cảnh & Triệu Chứng
- Khi chạy `inspect_machine.py` hoặc các tác vụ ADB cục bộ trên Kibe Local, lệnh bị treo vô tận hoặc báo `cannot connect to daemon / failed to start daemon`.
- Trong khi đó, cụm Admin Remote (`192.168.110.119:5037`) vẫn nhận 79–80 máy bình thường.

### Nguyên Nhân Gốc Rễ (Root Cause)
1. **Phần mềm Tiểu Vi (攸卫投屏 / xiaowei.exe):** Có binary riêng tại `C:\Program Files (x86)\xiaowei\tools\adb.exe`.
2. **Bẫy Port 5038 trong Watchdog cũ:** Watchdog tự đóng Tiểu Vi (`xiaowei_idle_auto_close_watchdog.py`) được thiết kế với giả định Tiểu Vi chỉ dùng port 5038.
   ```powershell
   # BUG CŨ: Bọc cứng trong $ports của 5038
   $ports = @(Get-NetTCPConnection -LocalPort 5038 -State Listen ...);
   if ($ports) { Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -in $ports ... } }
   ```
   Nếu tiến trình `adb.exe` của Tiểu Vi bị treo hoặc spawn ở cổng **5037** (cổng chính của Farm), câu lệnh PowerShell trên bỏ qua 100%, biến nó thành tiến trình zombie chiếm cổng 5037 không phản hồi TCP ACK.
3. **Farm Canonical ADB:** Farm chuẩn sử dụng binary tại `C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe`. Bất kỳ `adb.exe` nào nằm trong `C:\Program Files (x86)\xiaowei\` khi `xiaowei.exe` đã tắt đều là **tiến trình mồ côi 100%**.

### Giải Pháp & Quy Chuẩn Fix O(1)
- **Mở rộng bộ lọc tiến trình mồ côi:** Gỡ bỏ điều kiện bao bọc `if ($ports)`. Bắt tất cả process `adb.exe` thỏa mãn:
  ```powershell
  ($ports -and $_.ProcessId -in $ports) -or $_.CommandLine -like "*-P 5038*" -or $_.ExecutablePath -like "*\xiaowei\*"
  ```
- **Dập 2 tầng:**
  1. Gửi `kill-server` ở port 5038.
  2. Nếu vẫn còn `adb.exe` thuộc Xiaowei, gửi tiếp `kill-server` mặc định qua `XIAOWEI_ADB_BIN` và dọn sạch bằng `Invoke-CimMethod -MethodName Terminate`.

---

## 2. Kỷ Luật Circuit Breaker Cho Wi-Fi Auto-Healer (Chống Bẫy Dập Nhả Vô Tận)

### Bối Cảnh Sự Cố (Case Máy 7 & Dòng S7)
- Cronjob `farm-wifi-auto-healer` chạy mỗi 5 phút/lần. Khi máy bị rớt IP hoặc bị AP Aruba từ chối kết nối (`ASSOCIATION_REJECTION`), script thực hiện:
  `svc wifi disable` -> nghỉ 1s -> `svc wifi enable` (Cấp 1) và `adbjoinwifi` (Cấp 2).
- **Hậu quả phần cứng:** Bị dập nguồn radio liên tục 288 lần/ngày khiến chip Wi-Fi Broadcom DHD PCIe trên Samsung S7 rơi vào trạng thái ngủ sâu D3 (`state DORMANT / NO-CARRIER`), đơ hoàn toàn card mạng.

### Invariant: CẤM Chỉ Pause Rồi Bỏ Quên — Bắt Buộc Ngắt Mạch (Circuit Breaker)
- Khi phát hiện script cứu hộ gây phản tác dụng trên một số máy, **tuyệt đối không được chỉ PAUSE cronjob rồi để đó**, vì các máy khác khi rớt mạng sẽ không có cơ chế tự phục hồi.
- BẮT BUỘC trang bị **Circuit Breaker (Ngắt mạch & Cooldown)**:
  1. **Ngưỡng thất bại tối đa (`MAX_FAILURES = 2`):** Một máy chỉ được dập nhả tối đa 2 lần liên tiếp.
  2. **Thời gian cách ly tĩnh (`COOLDOWN = 1800s` / 30 phút):** Sau 2 lần thất bại, đưa máy vào danh sách Cooldown trong 30 phút. Trong thời gian này, các cữ cron 5 phút tiếp theo **BỎ QUA** máy này, tạo không gian tĩnh cho stack Wi-Fi và AP đàm phán lại.
  3. **Auto-Reset khi nhận IP:** Ngay khi máy có lại IP `192.168.110.X`, tự động reset bộ đếm lỗi về 0.

---

## 3. Phân Biệt Lỗi Rớt Proxy Thật vs ADB Socket/USB Drop

### Bẫy Báo Cáo "blocked by proxy VPN preflight"
- Trong `automation_core/preflight.py`, hàm `check_android_vpn()` kiểm tra IP Wi-Fi và Proxy qua lệnh ADB.
- Khi cáp USB bị lỏng, thiết bị mất kết nối hoặc ADB Daemon bị treo cổng 5037, lệnh ADB ném ra lỗi `device offline or ADB/USB disconnected`.
- Cơ chế fail-closed tự động gán nhãn:
  `final_status: blocked-proxy-vpn` | `message: [device-lock] machine X blocked by proxy VPN preflight`.
- **Kỷ luật điều phối:** Không vội vàng kết luận là proxy rớt mạng. Bắt buộc:
  1. Đọc trường `stop_reason` thật trong `summary.txt` (nếu có `device offline / not found` $\rightarrow$ lỗi phần cứng/USB/ADB, không phải proxy).
  2. Kiểm tra log của `cron_mobiproxy_healer.py` (`D:/Taadaa/AI-Tools/logs/mobiproxy_healer.log`) để xác thực trạng thái thật của cụm 32 cổng proxy.

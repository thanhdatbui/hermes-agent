# Xiaowei Orphan ADB Port 5037 Hijack & Wi-Fi Healer Circuit Breaker Pattern

## 1. Sự Cố Xiaowei Orphan ADB Chiếm Cổng 5037 (Port 5037 Hijack)

### Hiện tượng
- Lệnh ADB cục bộ trên Kibe (`inspect_machine.py`, `adb devices`, runner) bị treo cứng socket TCP cổng 5037 (Timeout hoặc Connection Refused 10061).
- Kiểm tra tiến trình thấy `xiaowei.exe` không hề chạy, nhưng cổng 5037 bị chiếm giữ bởi PID mồ côi của binary `C:\Program Files (x86)\xiaowei\tools\adb.exe` với command line:
  `['adb', '-L', 'tcp:localhost:5037', 'fork-server', 'server']`.

### Nguyên nhân gốc (Root Cause)
- Watchdog tự đóng Tiểu Vi (`xiaowei_idle_auto_close_watchdog.py`) được thiết kế ban đầu để dọn tiến trình stream phụ trên cổng 5038:
  ```powershell
  # CODE CŨ DÍNH BẪY BÓ HẸP CỔNG:
  $ports = @(Get-NetTCPConnection -LocalPort 5038 -State Listen ...);
  if ($ports) { Get-CimInstance Win32_Process -Filter "Name = 'adb.exe'" | Where-Object { $_.ProcessId -in $ports ... } }
  ```
- Khi Tiểu Vi khởi động hoặc gặp crash, nó spawn `adb.exe` riêng của nó gắn vào cổng **5037**. Khi người dùng đóng Tiểu Vi, watchdog kiểm tra thấy không có process nào ở cổng 5038 nên bỏ qua hoàn toàn.
- Hậu quả: Tiến trình `adb.exe` của Tiểu Vi tiếp tục sống sót ở cổng 5037, cướp quyền của ADB Server chuẩn của Farm (`C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe`) và gây đóng băng toàn bộ cụm Kibe Local.

### Quy chuẩn vá bắt buộc (Patch Contract)
1. **Gỡ bỏ điều kiện bao bọc `if ($ports)`**: Truy vấn CIM bắt buộc nhận diện mọi tiến trình `adb.exe` thỏa mãn:
   ```powershell
   Get-CimInstance Win32_Process -Filter "Name = 'adb.exe'" | Where-Object { 
       ($ports -and $_.ProcessId -in $ports) -or 
       $_.CommandLine -like "*-P 5038*" -or 
       $_.ExecutablePath -like "*\xiaowei\*" 
   }
   ```
2. **Dọn sạch khi Tiểu Vi tắt**: Khi `is_xiaowei_running()` trả về `False`, bất kỳ `adb.exe` nào thuộc thư mục `*\xiaowei\*` đều phải bị tiêu diệt dứt điểm (qua `kill-server` và CIM fallback) để trả lại cổng 5037 cho Farm.
3. **Giới hạn phạm vi `_try_kill_server()` (Sol Auditor Invariant)**: `_try_kill_server()` chỉ được gọi `[XIAOWEI_ADB_BIN, "-P", "5038", "kill-server"]`, tuyệt đối KHÔNG gọi `kill-server` mặc định (không có `-P 5038`) vì sẽ làm sập ADB daemon cổng 5037 chính của Farm. Việc dọn tiến trình mồ côi Tiểu Vi ở các cổng khác hoặc không có port bắt buộc để `_try_cim_terminate()` xử lý an toàn theo `ExecutablePath`.
4. **Tránh xung đột phiên bản ADB (Protocol Fault - Connection Reset)**: Tiểu Vi dùng ADB v34 (`C:\Program Files (x86)\xiaowei\tools\adb.exe`), trong khi GemPhoneFarm dùng ADB v35 (`C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe`). Mọi script kiểm tra (`inspect_machine.py`, runner) bắt buộc ưu tiên binary v35 của GemPhoneFarm trước; nếu trỏ nhầm client v34 vào daemon v35 sẽ văng lỗi `protocol fault (couldn't read status): connection reset`.

---

## 2. Bẫy Đặt Tên Báo Cáo "blocked-proxy-vpn" Trong Runner Preflight

### Hiện tượng & Hiểu lầm
- Runner báo cáo: `final_status: blocked-proxy-vpn` kèm lý do: `[device-lock] machine X blocked by proxy VPN preflight`.
- Operator/User đọc báo cáo thường kết luận: *"Proxy rớt mạng hoài"*, *"Modem MobiProxy hoặc MikroTik bị sập"*.

### Sự thật kỹ thuật
- Trong `automation-core/src/automation_core/preflight.py`, hàm `check_android_vpn()` là cơ chế **Fail-Closed Shield** (chống lộ IP FPT gốc). Trước khi bật TikTok, script chạy:
  `adb.shell(["ip", "addr", "show", "wlan0"])`.
- Khi máy bị **lỏng cáp USB, rơi vào chế độ sleep sâu, hoặc ADB daemon bị treo socket**, lệnh ADB văng lỗi:
  `stop_reason: device is offline or ADB/USB disconnected for <serial>: adb.exe: device not found`.
- Hàm `check_android_vpn()` bắt ngoại lệ kết nối, trả về `AndroidVpnPreflight(connected=False, transport_lost=True)`. Runner gom tất cả các trường hợp preflight không qua vào nhãn **`blocked-proxy-vpn`**.
- **Kỷ luật đối soát:** Luôn đọc trường `stop_reason` và `error` bên dưới `summary.txt` để phân biệt chính xác:
  * Lỗi Proxy thật: `tun0 VPN egress IP verification failed` hoặc `settings global http_proxy is :0`.
  * Lỗi phần cứng/ADB: `device offline or ADB/USB disconnected`.

---

## 3. Kỷ Luật Thiết Kế Auto-Healer: Circuit Breaker Bắt Buộc

### Bẫy Dập Nhả Wi-Fi Vô Tận (Threshing Loop)
- Một script cứu hộ tự động (`farm_wifi_auto_healer.py`) chạy định kỳ ngắn (ví dụ mỗi 5 phút) hễ thấy máy chưa có IP là tự động toggle:
  `svc wifi disable` $\rightarrow$ `sleep 1.0` $\rightarrow$ `svc wifi enable`.
- **Hậu quả phần cứng:** Trên Samsung Galaxy S7 (driver Broadcom DHD PCIe), việc dập nguồn radio liên tục khiến card mạng rơi vào trạng thái ngủ sâu D3 (`state DORMANT / NO-CARRIER`), bị AP Aruba từ chối bắt tay (`ASSOCIATION_REJECTION`) và đóng băng hoàn toàn.

### Nguyên tắc Circuit Breaker & Cooldown
Tuyệt đối **KHÔNG PAUSE vĩnh viễn** cron auto-healer khi gặp lỗi (khiến toàn farm mất cơ chế tự phục hồi mạng). BẮT BUỘC nhúng cơ chế ngắt mạch:
1. **Ngưỡng chịu lỗi (`MAX_FAILURES = 2`)**: Một máy chỉ được tự động heal tối đa 2 lần liên tiếp.
2. **Thời gian Cooldown (`COOLDOWN = 1800s` - 30 phút)**: Nếu sau 2 lần dập nhả mà máy vẫn chưa nhận IP (do lỗi AP Aruba từ chối hoặc anten lỏng), script phải **cách ly máy đó trong 30 phút**, bỏ qua không can thiệp để card mạng có không gian tĩnh tự kết nối lại.
3. **Auto-Reset**: Ngay khi máy nhận được IP `192.168.110.X`, bộ đếm lỗi tự động xóa về 0.

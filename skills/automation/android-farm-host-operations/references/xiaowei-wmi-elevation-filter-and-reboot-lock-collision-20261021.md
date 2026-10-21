# Chẩn Đoán Lỗi WMI Elevation Lọc Cổng 5038 & Xung Đột Khóa Reboot 3 Ca (21/10/2026)

## 1. Hiện Tượng Thực Tế
- Trên host Kibe PC, sau Ca 3 (Tối) ngày 21/10/2026, 35/80 máy bị văng kết nối ADB/USB và lỗi mở app TikTok.
- Uptime của cả 2 máy Kibe và Admin đều đã tích tụ hơn 17.5 tiếng (từ 05:21 sáng đến 23:00 đêm) mà không hề khởi động lại, dù hệ thống có Task Scheduler reboot 3 ca (05:20, 11:20, 17:20).
- Cổng ADB 5038 của XiaoWei (`adb.exe -P 5038 nodaemon server start`, PID 15812) mở từ 16:38:23 nhưng watchdog dọn cổng (`xiaowei-idle-auto-close-kibe`) chạy mỗi 2 phút vẫn báo OK và không hề hạ tiến trình mồ côi này.

---

## 2. Phân Tích Kỹ Thuật (Root Cause 1: Bẫy WMI Elevation / Process Integrity)
1. **Lệnh lọc cổng 5038 trong `xiaowei_idle_auto_close_watchdog.py`:**
   ```powershell
   $ports = @(Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { [int]$_.OwningProcess })
   if ($ports) {
       Get-CimInstance Win32_Process -Filter "Name = 'adb.exe'" | Where-Object {
           $_.ProcessId -in $ports -and ($_.CommandLine -like "*-P 5038*" -or $_.ExecutablePath -like "*\xiaowei\*")
       }
   }
   ```
2. **Cơ chế bảo mật Windows WMI:**
   - Khi XiaoWei được khởi chạy dưới quyền Administrator / Elevated Integrity Level, các tiến trình con (`adb.exe`) cũng kế thừa integrity level này.
   - Khi tiến trình cron/watchdog của Hermes chạy dưới user thường truy vấn `Get-CimInstance Win32_Process`, Windows **từ chối cấp quyền đọc `CommandLine` và `ExecutablePath`** của tiến trình có mức đặc quyền cao hơn (trả về `$null`).
3. **Hệ quả lọc nhầm:**
   - Biểu thức so sánh `$null -like "*-P 5038*"` trả về `$false`.
   - `Count` của process trả về `0` $\rightarrow$ hàm `is_xiaowei_adb_running()` luôn trả về `False`.
   - Guard `if is_xiaowei_adb_running() is not True: return False` coi như không có ADB 5038 mồ côi và thoát im lặng.
4. **Giải pháp chuẩn hóa O(1):**
   - Không phụ thuộc vào WMI `CommandLine` hay `ExecutablePath`.
   - Khi cổng 5038 đã xác định có kết nối listening qua `psutil.net_connections(kind='tcp')`, chỉ cần kiểm tra `proc.name() == 'adb.exe'`. Không có bất kỳ tiến trình ADB nào khác ngoài XiaoWei nghe trên cổng 5038.
   - Hoặc dùng PowerShell: `Get-Process -Id $ports | Where-Object { $_.ProcessName -eq 'adb' }`.

---

## 3. Phân Tích Kỹ Thuật (Root Cause 2: Xung Đột Khóa Reboot 3 Ca & Bẫy One-Shot Trigger)
1. **Bẫy One-Shot Trigger của Task Scheduler:**
   - Task `Taadaa_Farm_Daily_Reboot_1135` chỉ phát lệnh đúng 1 lần tại giây `05:20:00`, `11:20:00`, `17:20:00`.
   - Nếu tại đúng giây đó có bất kỳ tiến trình nào giữ `active device lock`, `farm_preflight_daily_reset.py` kích hoạt nhánh an toàn `[SKIP]` để không cắt ngang máy.
   - Do chỉ có 1 trigger duy nhất không có retry/re-check sau 5–10 phút, cả ca đó bị trôi hoàn toàn.
2. **Xung đột Safe Window với Cron xen ca (`tiktok_rename_rolling_watchdog.py`):**
   - Hàm `is_safe_window()` của rolling rename cho phép chạy trong khung:
     `((570, 680), (930, 1040), (1290, 1425))`
   - Mốc 680 phút chính là `11:20`, mốc 1040 phút chính là `17:20`.
   - Cron chạy mỗi 15 phút (`*/15 * * * *`), nhận batch đổi tên vào lúc `11:15` và `17:15`.
   - Batch đổi tên chạy mất 5–10 phút, do đó tại đúng `11:20:02` và `17:20:02`, các lock `machine_*.lock.json` luôn ở trạng thái `running`.
3. **Giải pháp chuẩn hóa:**
   - Bắt buộc áp dụng **Reboot Blackout Buffer 20 phút** theo chuẩn skill `cron-reboot-window-safety`: Safe Window của mọi cron xen ca phải kết thúc trước `11:00` và `17:00` (`hm < 660`, `hm < 1020`).
   - Bổ sung cơ chế retry cho Task Scheduler hoặc cron reboot trong khung `11:20–11:40` và `17:20–17:40` (chờ lock nhả tối đa 3 lần x 5 phút) thay vì fail-closed 1 phát bỏ luôn cả ca.

# Dual ADB Server Device Split & Port 5038 Collision (15/10/2026)

## 1. Hiện Tượng & Triệu Chứng Thực Tế
- **Triệu chứng:** Runner nuôi TikTok, đăng video hoặc bật 2FA trên Farm Admin (M201–280) đồng loạt báo lỗi app thất bại hàng loạt (chỉ ~20 máy thành công, 50+ máy thất bại).
- **Các thông báo lỗi điển hình:**
  * `prepare-tiktok failed to focus TikTok after launch` (lỗi lặp lại trên 10–15 máy).
  * `focused package is unknown` hoặc `focused_package: null` trong `details` của `log.jsonl`.
  * `run plan max_duration_seconds exceeded` và `hard outer watchdog deadline expired` (phiên nuôi kéo dài > 70 phút).
  * `device '<serial>' not found` dù máy điện thoại vẫn đang cắm cáp và màn hình sáng.
- **Hiện tượng nghịch lý khi đối soát phần cứng:**
  * Windows Device Manager (PowerShell `Get-PnpDevice | Where-Object { $_.FriendlyName -like '*ADB*' }`) báo **79 thiết bị OK**, 0 thiết bị lỗi.
  * Tuy nhiên lệnh `adb devices` qua cổng mặc định 5037 (`adb -H 192.168.110.119 -P 5037 devices`) chỉ trả về **37 thiết bị**, mất tích hoàn toàn **43 thiết bị**.

---

## 2. Bản Chất Kỹ Thuật (Root Cause)
1. **Xung đột 2 Daemon ADB chạy song song:**
   * Trên host Windows (Admin PC), xuất hiện một tiến trình con hoặc tool khởi động một server ADB thứ hai chạy trên cổng không chuẩn:
     `"C:\Program Files (x86)\xiaowei\tools\adb.exe" tools/adb -P 5038 nodaemon server start` (PID `12296`).
   * Đồng thời, server ADB mặc định của hệ thống vẫn đang chạy trên cổng chuẩn 5037:
     `"C:\Program Files (x86)\xiaowei\tools\adb.exe" -a nodaemon server start` (PID `16388`).
2. **WinUSB Endpoint Hijacking & Chia Rẽ Thiết Bị:**
   * Driver WinUSB trên Windows cấp phát interface USB độc quyền (exclusive interface handle) cho tiến trình mở kết nối trước.
   * Khi 2 daemon ADB cùng quét các cổng USB:
     * Daemon 1 (port 5037) giành được 37 máy.
     * Daemon 2 (port 5038) giành được 42–43 máy còn lại.
   * Toàn bộ automation script, runner và watchdog (kết nối mặc định tới port 5037) **hoàn toàn mù với 42 máy thuộc quyền quản lý của port 5038**.
   * Khi runner gọi `dumpsys window` hoặc `get_focused_activity`, daemon 5037 trả về rỗng hoặc `device not found`, khiến runner retry 10 lần rồi đánh dấu nhầm thành `prepare-tiktok failed to focus TikTok after launch`.

---

## 3. Quy Trình Chẩn Đoán O(1) Bằng Bằng Chứng Thép
1. **Kiểm tra số lượng tiến trình ADB trên Admin-PC:**
   ```powershell
   Get-Process -Name adb | Select-Object Id, ProcessName, StartTime, CPU, WorkingSet
   ```
   Nếu thấy $\ge 2$ tiến trình `adb.exe`, kiểm tra command line và port:
   ```powershell
   Get-CimInstance Win32_Process -Filter "Name = 'adb.exe'" | Select-Object ProcessId, CommandLine
   ```
2. **Đối soát thiết bị trên từng cổng ADB:**
   * Cổng chuẩn:
     ```bash
     adb -H 192.168.110.119 -P 5037 devices
     ```
   * Cổng phụ (5038):
     ```bash
     adb -H 192.168.110.119 -P 5038 devices
     ```
   * Nếu danh sách máy bị chia đôi giữa 5037 và 5038, đây chính là hiện tượng Split ADB Daemon.

---

## 4. Quy Trình Khôi Phục O(1) Chuẩn Xác
1. **Cưỡng chế hạ gục daemon rogue port 5038:**
   Dùng `Stop-Process` qua `admin_ssh.py`:
   ```powershell
   Stop-Process -Name adb -Force
   ```
   (Lệnh này sẽ dập toàn bộ các daemon ADB cũ đang tranh chấp).
2. **Khởi động lại duy nhất 1 daemon ADB chuẩn trên port 5037:**
   ```cmd
   cmd.exe /c start /b "" "C:\Program Files (x86)\xiaowei\tools\adb.exe" -a nodaemon server
   ```
3. **Đối soát phục hồi:**
   Chạy `python D:/Taadaa/tools/inspect_machine.py` để xác nhận danh sách `List of devices attached` trên Admin Remote hồi phục đủ 78–79 máy.

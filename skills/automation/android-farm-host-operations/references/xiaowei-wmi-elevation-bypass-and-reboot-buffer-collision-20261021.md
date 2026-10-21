# XiaoWei WMI Elevation Bypass & Inter-Shift Cron Reboot Buffer Collision (21/10/2026)

## 1. Vấn Đề 1: Bẫy Phân Quyền WMI Khiến Watchdog Bỏ Qua ADB 5038 Mồ Côi

### Hiện Tượng
- Watchdog `xiaowei-idle-auto-close-kibe` (`xiaowei_idle_auto_close_watchdog.py`) chạy đều đặn mỗi 2 phút, báo `last_status: ok`.
- Tiến trình `adb.exe -P 5038 nodaemon server start` (PID 15812) vẫn sống sót suốt gần 7 tiếng (từ 16:38 đến 23:45), chiếm giữ độc quyền WinUSB endpoint và giam giữ 35 máy khỏi cổng 5037 của farm.

### Nguyên Nhân Gốc Rễ
1. **Tiến trình Elevated:** App XiaoWei hoặc daemon ADB con của nó chạy ở mức High Integrity Level (Elevated/Administrator).
2. **Hạn chế bảo mật của WMI:**
   Code cũ dùng PowerShell:
   ```powershell
   Get-CimInstance Win32_Process -Filter "Name = 'adb.exe'" | Where-Object { $_.ProcessId -in $ports -and ($_.CommandLine -like "*-P 5038*" -or $_.ExecutablePath -like "*\xiaowei\*") }
   ```
   Khi caller (Hermes daemon) chạy dưới standard user, Windows WMI trả về `$null` cho cả `CommandLine` và `ExecutablePath` của tiến trình elevated.
3. **Guard Fail-Open thành Fail-Skip:**
   Điều kiện lọc `$null -like "*-P 5038*"` trả về `False` $\rightarrow$ `Count` = 0 $\rightarrow$ `is_xiaowei_adb_running()` trả về `False`.
   Hàm dọn dẹp kiểm tra `if is_xiaowei_adb_running() is not True: return False` coi như không có ADB 5038 nào đang chạy và thoát im lặng.

### Chuẩn Hóa Giải Pháp (O(1) psutil)
- Bỏ hoàn toàn việc parse WMI/CIM CommandLine.
- Dùng `psutil.net_connections(kind="tcp")` trực tiếp từ Python:
  ```python
  if psutil is not None:
      try:
          for c in psutil.net_connections(kind="tcp"):
              port = getattr(c.laddr, "port", None) if hasattr(c, "laddr") else None
              if port == XIAOWEI_ADB_PORT and getattr(c, "status", "") == "LISTEN":
                  return True
          return False
      except Exception:
          pass
  ```
- Kiểm tra socket TCP cổng 5038 phản hồi trong < 2ms, không bị ảnh hưởng bởi UAC/Integrity Level, 100% đáng tin cậy.

---

## 2. Vấn Đề 2: Cron Xen Ca Gây Deadlock Mất Mốc Reboot 11:20 & 17:20

### Hiện Tượng
- Task Scheduler `Taadaa_Farm_Daily_Reboot_1135` có kích hoạt lúc 11:20 và 17:20.
- Log `daily_reset.log` ghi nhận:
  `[SKIP] Dang co tien trinh nuoi acc giu active device lock. Bo qua reboot de khong cat ngang ca chay.`
- Máy Kibe và Admin chạy liên tục >17.5 tiếng không reboot xả đệm controller USB 2.0 EHCI.

### Nguyên Nhân Gốc Rễ
1. **Safe Window rướn sát giờ reboot:**
   Script đổi biệt danh `tiktok_rename_rolling_watchdog.py` có safe window:
   `((570, 680), (930, 1040), (1290, 1425))` (680 phút = 11:20, 1040 phút = 17:20).
2. **Xung đột chu kỳ cron:**
   Cron chạy mỗi 15 phút $\rightarrow$ các tick lúc **11:15** và **17:15** vẫn nằm trong Safe Window nên nhận batch đổi tên.
   Thao tác đổi tên kéo dài 5–10 phút, dẫn đến tại đúng mốc **11:20:00** và **17:20:00** thì `machine_*.lock.json` vẫn mang `status: running`.
3. **One-shot Trigger không có Retry:**
   Task Scheduler chỉ gọi 1 lần tại mốc 11:20/17:20. Khi bị skip, toàn bộ mốc reboot của ca đó bị mất trắng.

### Chuẩn Hóa Giải Pháp (20-Minute Pre-Reboot Buffer)
- Rút ngắn `SAFE_IDLE_WINDOWS` trong mọi cron xen ca (như đổi tên, 2FA, avatar) kết thúc trước giờ reboot ít nhất 20 phút:
  `SAFE_IDLE_WINDOWS = ((9 * 60 + 30, 11 * 60), (15 * 60 + 30, 17 * 60), (21 * 60 + 30, 23 * 60 + 45))`
  (Sáng: 09:30–11:00; Chiều: 15:30–17:00).
- Đảm bảo các tác vụ con nhả sạch lock trước 11:15 và 17:15, giải phóng 100% tài nguyên cho `daily_reset.py` thực thi an toàn.

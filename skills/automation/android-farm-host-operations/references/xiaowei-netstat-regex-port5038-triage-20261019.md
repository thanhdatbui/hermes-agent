# Chẩn Đoán Lỗi Regex Netstat Gây Tê Liệt Watchdog Dọn Cổng 5038 Của XiaoWei (19/10/2026)

## 1. Hiện Tượng Thực Tế
- Trên host Kibe PC, app XiaoWei đã tắt nhưng lệnh `adb devices` trên cổng mặc định 5037 chỉ trả về 40 máy (trong khi thực tế có 65 máy đang cắm cáp).
- 25 máy còn lại (trong đó có Máy 52) bị kẹt ở cổng 5038 do tiến trình `adb.exe -P 5038 nodaemon server start` mồ côi chiếm giữ.
- Mặc dù cron watchdog `xiaowei-idle-auto-close-kibe` (`xiaowei_idle_auto_close_watchdog.py`) chạy đều đặn mỗi 2 phút, cổng 5038 vẫn không được dọn dẹp.

## 2. Phân Tích Kỹ Thuật (Root Cause)
1. **Lệnh kiểm tra cổng 5038:**
   Hàm `is_xiaowei_adb_running()` sử dụng PowerShell:
   ```powershell
   $ports = (netstat -ano -p tcp | Select-String ':{XIAOWEI_ADB_PORT}\s+LISTENING') | ForEach-Object { ($_ -split '\s+')[-1] }
   ```
2. **Cấu trúc thực tế của `netstat -ano`:**
   Trên Windows, mỗi dòng TCP in ra 5 cột:
   `Proto   Local Address          Foreign Address        State           PID`
   `TCP     127.0.0.1:5038         0.0.0.0:0              LISTENING       10084`
   Nằm giữa Local Address (`:5038`) và State (`LISTENING`) luôn là Foreign Address (`0.0.0.0:0`).
3. **Lỗi Kép: Regex Thiếu Foreign Address & Trailing Newline Làm Rỗng Index `[-1]`:**
   - Chuỗi `':{XIAOWEI_ADB_PORT}\s+LISTENING'` chỉ cho phép ký tự khoảng trắng giữa `:5038` và `LISTENING`. Do có `0.0.0.0:0` ở giữa, regex không bao giờ match.
   - Ngay cả khi sửa regex thành `:{XIAOWEI_ADB_PORT}\s+\S+\s+LISTENING`, lệnh PowerShell `($_ -split '\s+')[-1]` vẫn bị rỗng (`""`): Dòng text của netstat kết thúc bằng `\r\n`, việc split theo `\s+` sinh ra phần tử cuối cùng rỗng ở `[-1]` (PID thực tế nằm ở `[-2]` nếu không Trim). Bắt buộc dùng `($_.Line.Trim() -split '\s+')[-1]` và ép kiểu `[int]`.
   - Bẫy WMI Integrity Level: Biểu thức `Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '*\xiaowei\*' }` có thể trả về `$null` cho `ExecutablePath`/`CommandLine` nếu caller không chạy quyền Administrator, dẫn đến lọc nhầm thành 0 process. Khi `$ports` đã được trích xuất từ cổng 5038, điều kiện lọc cần kết hợp: `Where-Object { $_.ProcessId -in $ports -and ($_.CommandLine -like "*-P 5038*" -or $_.ExecutablePath -like "*\xiaowei\*") }`.
4. **Hậu quả:**
   `$ports` luôn rỗng -> `is_xiaowei_adb_running()` luôn trả về `False`.
   Hàm `cleanup_orphan_xiaowei_adb()` có điều kiện guard:
   `if DRY_RUN_MODE or is_xiaowei_running() is True or is_xiaowei_adb_running() is not True: return False`
   Vì `is_xiaowei_adb_running()` trả về `False`, guard coi như không có ADB 5038 nào đang chạy và thoát im lặng.

## 3. Khắc Phục & Chuẩn Hóa
1. **Dùng Native Cmdlet Chuẩn Nhất:**
   ```powershell
   $ports = @(Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { [int]$_.OwningProcess })
   ```
2. **Dùng Netstat Regex Chuẩn Khi Fallback:**
   ```powershell
   $ports = @(netstat -ano -p tcp | Select-String ':{XIAOWEI_ADB_PORT}\s+\S+\s+LISTENING' | ForEach-Object { [int]($_.Line.Trim() -split '\s+')[-1] })
   ```
3. **Bộ lọc Process An Toàn & Đủ Chặt:**
   ```powershell
   Get-CimInstance Win32_Process -Filter "Name = 'adb.exe'" | Where-Object { $_.ProcessId -in $ports -and ($_.CommandLine -like "*-P 5038*" -or $_.ExecutablePath -like "*\xiaowei\*") }
   ```
4. **Kiểm tra trực tiếp từ Python (O(1)):**
   ```python
   import psutil
   for c in psutil.net_connections(kind='tcp'):
       if c.laddr.port == 5038 and c.status == 'LISTEN':
           # Found PID c.pid
   ```

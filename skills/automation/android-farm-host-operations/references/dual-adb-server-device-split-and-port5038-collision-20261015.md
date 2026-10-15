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

## 2. Bản Chất Kỹ Thuật (Root Cause) & Nguồn Gốc Tiến Trình Mồ Côi
1. **Xung đột 2 Daemon ADB chạy song song & Nguồn gốc port 5038:**
   * Phần mềm **Tiểu Vi / Xiaowei (极卫)** khi mở lên luôn tự spawn một server ADB riêng chạy trên cổng 5038:
     `"C:\Program Files (x86)\xiaowei\tools\adb.exe" tools/adb -P 5038 nodaemon server start` (PID `12296`, parent là tiến trình `xiaowei.exe`).
   * **Bẫy tiến trình mồ côi (Orphan Daemon):** Khi `xiaowei.exe` bị tắt hoặc bị watchdog đóng (`taskkill /F /IM xiaowei.exe`), Windows không tự động kill các tiến trình con. Daemon `adb.exe -P 5038` bị sót lại chạy ngầm vô thời hạn.
   * Đồng thời, server ADB mặc định của hệ thống vẫn đang chạy trên cổng chuẩn 5037:
     `"C:\Program Files (x86)\xiaowei\tools\adb.exe" -a nodaemon server start` (PID `16388`).
2. **WinUSB Endpoint Hijacking & Chia Rẽ Thiết Bị:**
   * Driver WinUSB trên Windows cấp phát interface USB độc quyền (exclusive interface handle) cho tiến trình mở kết nối trước.
   * Khi 2 daemon ADB cùng quét các cổng USB:
     * Daemon 1 (port 5037) giành được 37 máy.
     * Daemon 2 (port 5038) giành được 42–43 máy còn lại.
   * Toàn bộ automation script, runner và watchdog (kết nối mặc định tới port 5037) **hoàn toàn mù với 42 máy thuộc quyền quản lý của port 5038**.
   * Khi runner gọi `dumpsys window` hoặc `get_focused_activity`, daemon 5037 trả về rỗng hoặc `device not found`, khiến runner retry 10 lần rồi đánh dấu nhầm thành `prepare-tiktok failed to focus TikTok after launch`.
3. **Bẫy Phân Loại Fallback của Watchdog:**
   * Trong `feed_session_watchdog.py`, hàm `classify_feed_failure` fallback mặc định về nhãn `"Lỗi App TikTok/Script"` cho mọi chuỗi lỗi không chứa rõ "device not found", "wifi", hay "proxy".
   * Do đó các lỗi nghẽn WinUSB/ADB timeout như `screen capture invalid`, `feed swipe command failed`, `focus lost` đều bị gom thành "Lỗi App TikTok/Script", gây hiểu lầm là app TikTok bị crash.

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

## 4. Quy Trình Khôi Phục O(1) Phẫu Thuật Không Gián Đoạn (Surgical Zero-Disruption Recovery)
*Lưu ý cốt lõi:* CẤM TUYỆT ĐỐI dùng `Stop-Process -Name adb -Force` bừa bãi nếu đang có batch nuôi acc, upload hoặc 2FA đêm chạy trên port 5037, vì kill toàn bộ adb sẽ làm crash tiến trình live đó!

1. **Bắn lệnh kill-server đích danh cổng 5038 (Phẫu thuật O(1)):**
   Qua SSH tới Admin PC, gọi trực tiếp binary adb của Xiaowei ra lệnh kill duy nhất server 5038:
   ```python
   python D:/Taadaa/tools/admin_ssh.py 'python -c "import subprocess; adb=r\"C:\Program Files (x86)\xiaowei\tools\adb.exe\"; print(subprocess.run([adb, \"-P\", \"5038\", \"kill-server\"], capture_output=True, text=True))"'
   ```
2. **Cơ chế tự giải phóng WinUSB:**
   - Ngay khi daemon 5038 thoát, 42 thiết bị đang bị chiếm giữ được WinUSB trả tự do lập tức.
   - Daemon chính trên port 5037 tự động handshake nhận lại 42 thiết bị này thành `device` trong vòng 1–2 giây mà **KHÔNG CẦN khởi động lại port 5037**, bảo toàn 100% các batch 2FA/nuôi acc đang chạy!
3. **Đối soát phục hồi tức thì:**
   Chạy lệnh kiểm đếm nhanh:
   ```python
   python D:/Taadaa/tools/admin_ssh.py 'python -c "import subprocess; adb=r\"C:\Program Files (x86)\xiaowei\tools\adb.exe\"; out=subprocess.run([adb, \"devices\"], capture_output=True, text=True).stdout; devs=[l.split()[0] for l in out.strip().splitlines()[1:] if \"device\" in l]; print(\"Total connected devices:\", len(devs))"'
   ```
   Xác nhận trả về đủ `Total connected devices: 79` và 0 máy offline.

---

## 5. Cơ Chế Bảo Hiểm Chống Tái Diễn & Nâng Cấp Watchdog Tự Động (Prevention Invariant)
1. **Lỗ hổng của Watchdog đóng Tiểu Vi cũ (`xiaowei_idle_auto_close_watchdog.py`):**
   - Chỉ dùng `taskkill /F /IM xiaowei.exe` thiếu cờ `/T` (Tree Kill), khiến tiến trình con `adb.exe -P 5038` không bị hạ sát khi app đóng.
   - Chỉ quét khi `is_xiaowei_running() == True`: Nếu người dùng tự đóng giao diện Tiểu Vi bằng tay (nút X), watchdog cũ im lặng thoát và bỏ rơi tiến trình `adb -P 5038` chạy vĩnh viễn.
2. **Cơ chế phòng thủ chủ động 2 lớp (Đã triển khai & đồng bộ):**
   - **Lớp 1 (Tree Kill):** Ép cờ `/T` trong `taskkill /F /T /IM xiaowei.exe` để diệt sạch cả cây tiến trình con.
   - **Lớp 2 (Orphan Cleaner Hook):** Cứ mỗi chu kỳ 5 phút, ngay cả khi Tiểu Vi KHÔNG chạy (`not is_xiaowei_running()`), watchdog tự động chạy hàm `cleanup_orphan_xiaowei_adb()` bắn `adb -P 5038 kill-server` dọn sạch mọi tiến trình mồ côi sót lại.
   - **Đồng bộ đa cụm:** Đồng bộ qua `cron_sync_watchdog.py` sang cả runtime Admin PC (`%LOCALAPPDATA%\hermes\scripts\xiaowei_idle_auto_close_watchdog.py`) và Kibe PC.
3. **Xử lý thiết bị kẹt socket USB transport sau khi giải phóng port 5038:**
   - Nếu thiết bị đã về `device` nhưng lệnh shell bị timeout (hung socket): Bắn `adb -s <serial> reconnect` để ép Linux kernel reset lại pipe `/dev/android_adb`. Thiết bị sẽ phản hồi trở lại bình thường trong < 1s mà không cần reboot.
   - Trong `farm_adb_transport_auto_healer.py`: BẮT BUỘC bọc `try...except Exception: pass` quanh `reconnect` và `keyevent 224` để timeout của một máy không làm crash toàn bộ batch khôi phục.


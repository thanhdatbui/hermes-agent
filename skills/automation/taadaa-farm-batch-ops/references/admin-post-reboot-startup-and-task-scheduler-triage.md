# Chẩn Đoán & Khắc Phục Tự Khởi Động Sau Reboot Cụm Admin (Startup & Task Scheduler Triage)

## 1. Triệu chứng & Bối cảnh
- **Triệu chứng**: Sau ca reboot định kỳ (05:20, 11:20, 17:20), watchdog `farm-render-download-watchdog` báo `Trạng thái download: ⚪ Đang dừng` và `Trạng thái render: ⚪ Đang dừng`.
- **Thắc mắc của User**: *"Là sao cài khi reboot máy tự động kích hoạt cào video r mà?"*
- **Kỳ vọng**: Hệ thống đã có file trong `shell:startup` (`start_downloader_watchdog.vbs`, `start_render_watchdog.vbs`) và các Windows Task Scheduler (`Taadaa_Admin_Downloader_Boot`, `Taadaa_Admin_Downloader_15m`...).

---

## 2. Hai Tử Huyệt Gốc Rễ Khiến Khởi Động Tự Động Bị Tê Liệt

### Tử huyệt 1: Silent Crash do Trỏ Nhầm Python Hệ Thống Thiếu Package
- **Cơ chế lỗi**: File `.vbs` khởi động (`start_downloader_watchdog.vbs`, `start_render_watchdog.vbs`) và launcher (`launch_detached_admin_render.py`) bị gán cứng đường dẫn Python hệ thống:
  `C:\Users\Admin\AppData\Local\Programs\Python\Python311\pythonw.exe`
- **Thực tế môi trường**: Python 3.11 hệ thống trên Admin **hoàn toàn KHÔNG có thư viện `psutil` và `openpyxl`**!
  - `watchdog_admin_downloader.py`: Dòng 4 có `import psutil`.
  - `watchdog_admin_render.py`: Dòng 2 có `import psutil`.
  - `run_admin_render_worker.py`: Dòng 3 có `import openpyxl`.
- **Hệ quả**: Khi Windows boot lên và nạp Startup, Python văng lỗi `ModuleNotFoundError: No module named 'psutil'` (hoặc `openpyxl`) và **chết ngay lập tức sau 0.1 giây trong im lặng** vì chạy qua `pythonw.exe` ngầm không mở cửa sổ console.
- **Môi trường chuẩn bắt buộc**:
  `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\pythonw.exe` (hoặc `python.exe`), nơi đã cài đầy đủ `psutil`, `openpyxl`, `yt-dlp`, `opencv-python`.

### Tử huyệt 2: Bẫy `LogonType: Interactive` Trong Windows Task Scheduler
- **Cơ chế lỗi**: 5 Task Scheduler đăng ký trên Admin (`Taadaa_Admin_Downloader_Boot`, `Taadaa_Admin_Downloader_15m`, `Taadaa_Admin_Render_Boot`, `Taadaa_Admin_Render_15m`, `Taadaa_Admin_Hermes_Boot`) bị Windows gán mặc định:
  `Principal.LogonType = Interactive`
- **Hệ quả**: Task Scheduler có cơ chế bảo vệ: task với `LogonType: Interactive` **CHỈ CHẠY KHI CÓ PHIÊN ĐĂNG NHẬP GUI TƯƠNG TÁC (Desktop Session)**. Khi máy tự reboot rạng sáng, Windows đứng ở màn hình khóa (Lock Screen), Task Scheduler thấy chưa có phiên tương tác nên **từ chối kích hoạt task** (cột `LastRunTime` hoàn toàn trống trơn dù trạng thái là `Ready`).

---

## 3. Quy Trình Chẩn Đoán O(1) Qua `admin_ssh.py`

### Bước 1: Kiểm tra Task Scheduler Liveness
```bash
python D:/Taadaa/tools/admin_ssh.py --powershell "Get-ScheduledTask -TaskName 'Taadaa_Admin*' | Select-Object TaskName, State, LastTaskResult, LastRunTime, NextRunTime | Format-Table -AutoSize"
```
- Nếu `LastRunTime` trống trơn $\rightarrow$ Task Scheduler bị kẹt ở rào cản `LogonType: Interactive`.

### Bước 2: Kiểm tra thư viện trong Python hệ thống vs venv
```bash
python D:/Taadaa/tools/admin_ssh.py --powershell "Test-Path 'C:\Users\Admin\AppData\Local\Programs\Python\Python311\Lib\site-packages\psutil'; Test-Path 'D:\CodexRuntime\tiktok-video\venv-core024\Lib\site-packages\psutil'"
```
- Nếu Python 3.11 trả về `False` còn venv trả về `True` $\rightarrow$ Khẳng định các launcher đang bị silent crash do sai môi trường Python.

### Bước 3: Đọc đuôi log render worker để bắt dấu vết crash
```bash
python D:/Taadaa/tools/admin_ssh.py --powershell "Get-Content C:\Users\Admin\admin_render_worker.log -Tail 15"
```
- Bắt bẫy: `ModuleNotFoundError: No module named 'openpyxl'` tại dòng 3 của `run_admin_render_worker.py`.

---

## 4. Kỷ Luật Khắc Phục Chuẩn Hóa
1. **Chuẩn hóa đường dẫn Python trong toàn bộ launcher**:
   - `C:\Users\Admin\start_downloader_watchdog.vbs`
   - `C:\Users\Admin\start_render_watchdog.vbs`
   - `C:\Users\Admin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\start_downloader_watchdog.vbs`
   - `C:\Users\Admin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\start_render_watchdog.vbs`
   - `C:\Users\Admin\launch_detached_admin_render.py`
   - `C:\Users\Admin\watchdog_admin_render.py`
   $\rightarrow$ BẮT BUỘC đổi toàn bộ `python_exe` sang:
   `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\pythonw.exe`

2. **Cấu hình Task Scheduler Không Phụ Thuộc Interactive Logon**:
   Đăng ký task chạy dưới quyền `SYSTEM` hoặc gán `LogonType = S4U` / `ServiceAccount` với `/ru SYSTEM` để task kích hoạt ngay khi boot (`/sc onstart`) độc lập hoàn toàn với việc có user đăng nhập desktop hay không:
   ```cmd
   schtasks /Change /TN "Taadaa_Admin_Downloader_Boot" /RU "SYSTEM"
   schtasks /Change /TN "Taadaa_Admin_Downloader_15m" /RU "SYSTEM"
   ```

3. **CẤM ĐỔ LỖI CHO 2FA KHI DOWNLOADER BỊ DỪNG (Anti-False-Attribution Invariant)**:
   Tác vụ 2FA chạy ADB trên điện thoại Android, còn video download chạy mạng/proxy MikroTik trên PC. Hai tác vụ hoàn toàn độc lập, không dùng chung tài nguyên hay cổng mạng. Khi downloader dừng, tuyệt đối CẤM suy diễn rằng máy bận 2FA hay đề xuất hoãn download chờ 2FA.

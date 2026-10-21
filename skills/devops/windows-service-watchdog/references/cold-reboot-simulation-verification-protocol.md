# Cold Reboot Simulation Verification Protocol & System PATH Hardening

## 1. Bối cảnh & Sai lầm phổ biến khi kiểm thử dịch vụ nền

### Sai lầm chết người: "Đang chạy trong phiên hiện tại = Đã sửa xong"
Khi sửa lỗi cho các tiến trình chạy ngầm (Downloader, Renderer, Crawler, Watchdog) trên máy Windows:
- Agent thường chạy script trực tiếp qua console hoặc SSH, thấy tiến trình sinh PID và log chạy là vội vàng kết luận "ĐÃ XỬ LÝ TRIỆT ĐỂ".
- **Thực tế:** Môi trường khi chạy trực tiếp qua SSH/Interactive Session hoàn toàn khác với môi trường khi Windows khởi động lại (Unattended Reboot sau ca 05:20, 11:20, 17:20):
  1. **Mất biến môi trường User:** Task Scheduler chạy dưới tài khoản `NT AUTHORITY\SYSTEM` (hoặc khởi động trước khi có user đăng nhập) **chỉ đọc System PATH trong Windows Registry (`HKLM`)**, hoàn toàn bỏ qua User PATH (`C:\Users\<User>\AppData\Local\...`).
  2. **Thiếu nhị phân phụ thuộc:** Các công cụ cài qua WinGet hoặc User Profile (`ffmpeg.exe`, `ffprobe.exe`, `git.exe`, `node.exe`) bị mất khỏi PATH. Lệnh `shutil.which('ffmpeg')` trả về `None`, dẫn đến lỗi `[WinError 2] The system cannot find the file specified` hoặc `exit code 1` lặp đi lặp lại mỗi 30 giây.
  3. **Task Scheduler báo ảo:** Task Scheduler ghi nhận `LastTaskResult: 0` vì file VBScript launcher trả về 0 sau khi spawn background process, che giấu hoàn toàn việc worker bên trong bị chết ngầm.

Người vận hành phản ánh xác đáng:
> *"Chắc chắn fix đc chưa? H đang chạy đâu có nghĩa reboot lại vẫn chạy"*
> *"Fix mấy vòng k xong v"*

---

## 2. Giao thức 5 bước kiểm chứng giả lập Cold Reboot (Cold Reboot Simulation Protocol)

Tuyệt đối **CẤM** báo cáo hoàn thành hoặc khẳng định hệ thống tự phục hồi sau reboot nếu chưa chạy đủ 5 bước kiểm chứng thực tế dưới đây:

### Bước 1: Cold Wipe (Đưa về trạng thái 0)
Cưỡng chế dừng toàn bộ các tiến trình liên quan (dịch vụ, watchdog, worker, encoder) để đưa hệ thống về trạng thái sạch như vừa tắt nguồn:
```powershell
Stop-Process -Name python, pythonw, ffmpeg -Force -ErrorAction SilentlyContinue
```
Kiểm tra lại xác nhận 0 tiến trình mục tiêu còn tồn tại.

### Bước 2: Kích hoạt đúng ngữ cảnh Boot qua Task Scheduler
**CẤM** tự chạy file `.py` hay `.vbs` bằng lệnh console. Phải kích hoạt chính xác tác vụ khởi động hệ thống (`Boot Task`) qua Task Scheduler để chạy dưới đúng phân quyền thực tế (`NT AUTHORITY\SYSTEM` hoặc cấu hình thực của task):
```cmd
schtasks /run /tn "Taadaa_Admin_Downloader_Boot"
schtasks /run /tn "Taadaa_Admin_Render_Boot"
```
Xác nhận `schtasks` trả về `SUCCESS` (exit code 0).

### Bước 3: Khoảng chờ lan truyền (Propagation Window: 10–15s)
Chờ 10–15 giây để chuỗi khởi động không đồng bộ thực thi đầy đủ:
`Task Scheduler` $\rightarrow$ `wscript.exe` $\rightarrow$ `watchdog.py` $\rightarrow$ `service.py` $\rightarrow$ `worker sub-processes / ffmpeg.exe`.

### Bước 4: Kiểm tra toàn diện cây tiến trình & Telemetry động
Không chỉ kiểm tra PID tồn tại, phải xác thực **3 chỉ số động (Dynamic Liveness)**:
1. **CPU Time tích lũy:** CPU cycles của các tiến trình con (`ffmpeg.exe`, `python.exe`) phải tăng dần qua các lần đo (chứng minh tiến trình đang tính toán thực sự, không bị treo deadlock hoặc sleep vô tận).
2. **File log tăng trưởng:** Đọc tail log, xác nhận có các dòng nghiệp vụ mới phát sinh (ví dụ: `[TELEMETRY:RESERVE_DECISION]`, `[SCAN]`, `[RENDER]`).
3. **Số liệu nghiệp vụ biến động:** Số clip/folder hoàn thành phải nhảy số thực tế trên đĩa (ví dụ: `total_rendered` tăng từ 18,655 $\rightarrow$ 18,662).

### Bước 5: Cố định System PATH trong Windows Registry (Hardening)
Để đảm bảo vĩnh viễn không bị mất công cụ sau bất kỳ ca reboot nào:
1. **Tiêm cứng System PATH:** Nếu công cụ nằm trong thư mục venv hoặc WinGet, ghi thẳng vào System Environment trong Registry:
   ```python
   import winreg
   key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment", 0, winreg.KEY_READ | winreg.KEY_SET_VALUE)
   path, typ = winreg.QueryValueEx(key, "Path")
   target_dir = r"D:\CodexRuntime\tiktok-video\venv-core024\Scripts"
   if target_dir not in path:
       winreg.SetValueEx(key, "Path", 0, typ, target_dir + ";" + path)
   winreg.CloseKey(key)
   ```
2. **Co-location nhị phân:** Sao chép các file thực thi cần thiết (`ffmpeg.exe`, `ffprobe.exe`) trực tiếp vào thư mục `Scripts/` của chính virtualenv đang chạy worker.
3. **Tiêm PATH trong code khởi chạy:** Tại hàm `main()` của service daemon, luôn có dòng:
   ```python
   os.environ["PATH"] = r"D:/CodexRuntime/tiktok-video/venv-core024/Scripts;" + os.environ.get("PATH", "")
   ```

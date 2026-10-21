# Khắc Phục Triệt Để Lỗi Downloader/Render Admin: Bẫy Quyền SYSTEM, Thiếu PATH FFmpeg & Kỷ Luật Nghiệm Thu End-to-End

## 1. Hiện Tượng Thực Tế & Lời Phàn Nàn Của Người Dùng
- **Hiện tượng:** Sau khi đã "fix" dịch vụ download/render trên máy Admin ở phiên trước, đến ca reboot định kỳ (05:20) hoặc khi watchdog báo cáo lúc 06:00, hệ thống vẫn báo:
  ```text
  🏢 FARM ADMIN (MÁY 201-280):
  📥 Video gốc (D:\video goc may 2):
  • Trạng thái download: ⚪ Đang dừng
  • Trạng thái render: ⚪ Đang dừng
  ```
- **Phản ứng của người dùng:** *"Clmm farm admin hqua fix vụ download r h vẫn báo về đéo download... Lồn mẹ mày fix mấy vòng k xong v"*.
- **Nguyên nhân gốc rễ dẫn tới "Fix nhiều vòng không xong":** Agent sửa lỗi theo kiểu chắp vá bề mặt, sửa xong tầng 1 nhưng không truy vết kiểm chứng xuyên suốt toàn bộ chuỗi thực thi (End-to-End Execution Chain), để sót các lỗi chết ngầm ở tầng 2 và tầng 3.

---

## 2. Bóc Tách 3 Tử Huyệt Kỹ Thuật Liên Hoàn Trên Máy Admin

### Tử huyệt 1: Môi trường ảo `venv-core024` thiếu thư viện `psutil`
- **Cơ chế lỗi:** Khi chuyển đổi launcher từ Python hệ thống (3.11) sang môi trường ảo `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\pythonw.exe`, agent giả định venv này đã có đủ thư viện.
- **Thực tế:** `venv-core024` **chưa từng cài `psutil`**.
- Khi máy reboot lúc 05:20, Task Scheduler gọi `start_downloader_watchdog.vbs` $\rightarrow$ gọi `pythonw.exe watchdog_admin_downloader.py`. Ngay dòng `import psutil`, script chết trong 0.05s với `ModuleNotFoundError: No module named 'psutil'`.
- Vì `pythonw.exe` chạy ngầm không có console và không ghi stderr ra file, Task Scheduler thấy tiến trình thoát nhanh nên ghi `LastTaskResult: 0`. Toàn bộ chuỗi dừng hoạt động từ 05:20 sáng.

### Tử huyệt 2: Bẫy PATH `ffmpeg/ffprobe` khi Task Scheduler chạy quyền `SYSTEM`
- **Cơ chế lỗi:** Để dịch vụ tự khởi động sau reboot mà không cần người dùng đăng nhập desktop (tránh kẹt Lock Screen), Task Scheduler được cấu hình chạy dưới tài khoản `SYSTEM` (`LogonType: ServiceAccount`).
- **Thực tế:** Tài khoản `SYSTEM` **CHỈ có biến môi trường System PATH** (`C:\Windows\system32;...`), hoàn toàn không thừa hưởng User PATH của user `Admin` (`C:\Users\Admin\AppData\Local\Microsoft\WinGet\Links`).
- Trong khi đó, `ffmpeg.exe` và `ffprobe.exe` được cài qua WinGet nằm trong thư mục của user `Admin`.
- Khi `run_admin_downloader_service.py` gọi `download_by_niche.py`, dòng 1312 kiểm tra:
  ```python
  if shutil.which(args.ffmpeg) is None or shutil.which(args.ffprobe) is None:
      raise SystemExit("Khong tim thay ffmpeg/ffprobe trong PATH")
  ```
- Kết quả: Dù watchdog đã spawn được service, nhưng cứ mỗi 30s `download_by_niche.py` bật lên lại bị văng ngay lập tức với `exit code 1: Khong tim thay ffmpeg/ffprobe trong PATH`.

### Tử huyệt 3: Tiến trình `pythonw.exe` mồ côi giữ file lock (`admin_downloader.lock`)
- **Cơ chế lỗi:** Khi kiểm tra và tắt tiến trình để khởi động lại dịch vụ, câu lệnh `Stop-Process -Name python` hoặc `pkill python` **CHỈ diệt `python.exe`**, hoàn toàn bỏ qua các tiến trình `pythonw.exe`.
- Các instance `pythonw.exe` cũ (đang chạy lặp lỗi hoặc dùng interpreter cũ) vẫn tồn tại trong RAM và tiếp tục giữ độc quyền file lock qua `msvcrt.locking`.
- Khi instance mới được khởi động, nó thấy lock bị chiếm nên in `[LOCK] Another downloader service is already running. Exiting.` và thoát ngay.

---

## 3. Quy Trình Khắc Phục Triệt Để & Bền Vững (3 Lớp Bảo Hiểm)

### Lớp 1: Bù thư viện và phòng thủ Zero-Hard-Dependency cho Watchdog
1. **Chép thư viện chuẩn vào venv:**
   Chép `psutil` và `psutil-7.2.2.dist-info` từ môi trường Python có sẵn của hệ thống sang `D:\CodexRuntime\tiktok-video\venv-core024\Lib\site-packages`.
2. **Hardening Watchdog chống crash:**
   Trong cả `watchdog_admin_downloader.py` và `watchdog_admin_render.py`, luôn bọc `import psutil` trong `try...except ImportError`:
   ```python
   try:
       import psutil
   except ImportError:
       psutil = None
   ```
   Nếu `psutil is None`, tự động fallback sang `wmic process where "name='python.exe' or name='pythonw.exe'" get commandline` để kiểm tra tiến trình.

### Lớp 2: Cố định vị trí và PATH cho FFmpeg / FFprobe
1. **Chép trực tiếp nhị phân vào venv Scripts:**
   Chép `ffmpeg.exe` và `ffprobe.exe` từ `C:\Users\Admin\AppData\Local\Microsoft\WinGet\Links\` trực tiếp vào `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\`.
2. **Tiêm cứng PATH trong service:**
   Ở đầu hàm `main()` của `run_admin_downloader_service.py` và `run_admin_render_worker.py`:
   ```python
   os.environ["PATH"] = r"D:/CodexRuntime/tiktok-video/venv-core024/Scripts;C:/Users/Admin/AppData/Local/Microsoft/WinGet/Links;" + os.environ.get("PATH", "")
   ```
   Đồng thời đảm bảo `run_admin_render_worker.py` trỏ đúng `python_exe = r"D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe"` (không dùng Python 3.11 thiếu openpyxl).

### Lớp 3: Dọn dẹp tiến trình mồ côi toàn diện
Trước khi khởi động lại dịch vụ:
1. Xác định chính xác PID của toàn bộ tiến trình liên quan qua `psutil.process_iter()`.
2. Diệt cả `python.exe` và `pythonw.exe` đang chạy service/worker cũ:
   ```python
   import psutil
   for p in psutil.process_iter(['pid', 'name', 'cmdline']):
       try:
           cmd = " ".join(p.info.get('cmdline') or [])
           if any(k in cmd for k in ['run_admin_downloader_service', 'run_admin_render_worker', 'download_by_niche']):
               p.kill()
       except (psutil.NoSuchProcess, psutil.AccessDenied):
           pass
   ```
3. Chờ 2 giây để OS tự động giải phóng file lock `msvcrt` rồi mới chạy watchdog.

---

## 4. Kỷ Luật Nghiệm Thu End-to-End (BẮT BUỘC ĐỦ 4 CHẶNG)

Khi xử lý các sự cố về dịch vụ nền/watchdog, **TUYỆT ĐỐI CẤM** dừng lại ở việc thấy watchdog trả về `exit code 0`. Bắt buộc phải thu thập bằng chứng thực tế qua 4 chặng:

| Chặng | Kiểm Tra | Lệnh Kiểm Chứng | Kết Quả Bắt Buộc |
|---|---|---|---|
| **1. Cú pháp & Import** | Cú pháp Python không lỗi | `python -m py_compile <file.py>` | Exit code 0, 0 syntax error |
| **2. Khởi tạo Service** | Service chạy và chiếm lock | `Get-Process -Name python, pythonw` | Thấy PID của service và worker con |
| **3. Tiến độ thực tế** | Worker ghi log và tải video | `Get-Content <log_p> -Tail 20` | Log xuất hiện các dòng tải video thực tế, không có dòng lỗi PATH |
| **4. Đối soát từ xa** | Watchdog Kibe nhận trạng thái xanh | Chạy `fetch_admin_stats_remote()` | `is_dl: True`, `src_ge45` hoặc `total_rendered` tăng delta thật |

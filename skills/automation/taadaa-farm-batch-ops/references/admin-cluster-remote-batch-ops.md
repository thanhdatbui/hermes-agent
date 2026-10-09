# Điều phối Remote Batch Ops Cụm Admin (Máy 201..280) qua SSH & Quy chuẩn Watchdog Báo cáo

## 1. Nguyên tắc Báo cáo Watchdog (User Invariant)
- **"Download xong thì không báo nữa"**: Khi kho video gốc toàn cụm đã đạt 100% ($\ge 30$ video cho cả 640/640 folder) và tiến trình downloader không chạy, watchdog `farm_render_download_watchdog.py` BẮT BUỘC **tự động ẩn mục 1 (Video gốc)**, chỉ hiển thị tập trung **Tiến độ Render Tik1..Tik8**.
- **Tiêu đề rút gọn**: Chuyển thành `📊 BÁO CÁO TIẾN ĐỘ FARM KIBE (RENDER)`.
- **Lịch gửi Farm Alert**: Chuyển từ chat riêng (`origin`) sang nhóm Farm Alert (`deliver='telegram:-5373649734'`) với tần suất định kỳ mỗi 6h (`0 */6 * * *` vào các mốc 00:00, 06:00, 12:00, 18:00).
- **Mandatory Cron Sync**: Mỗi khi cập nhật `jobs.json` qua tool cronjob, bắt buộc chạy ngay `python C:/Users/Kibe/AppData/Local/hermes/scripts/cron_sync_watchdog.py` để đồng bộ sang cả Git Deploy và OneDrive Shared.

---

## 2. Kỹ thuật Vận hành Từ Xa qua SSH trên Windows Admin
- **Kết nối SSH**: Cấu hình alias `admin-farm` trỏ tới `192.168.110.119`, user `Admin`, key ed25519 không mật khẩu.
- **Bẫy mã hóa Unicode (UnicodeEncodeError cp1252)**:
  - Khi SSH sang Windows, môi trường CMD/PowerShell mặc định dùng `cp1252`. Các chuỗi tiếng Việt hoặc log UTF-8 sẽ gây crash `UnicodeEncodeError: 'charmap' codec can't encode character...`.
  - **Khắc phục**:
    1. Thiết lập biến môi trường `set PYTHONIOENCODING=utf-8` trước khi gọi script.
    2. Trong code Python, luôn thêm khối reconfigure đầu file:
       ```python
       try:
           if hasattr(sys.stdout, "reconfigure"):
               sys.stdout.reconfigure(encoding="utf-8", errors="replace")
           if hasattr(sys.stderr, "reconfigure"):
               sys.stderr.reconfigure(encoding="utf-8", errors="replace")
       except Exception:
           pass
       ```
- **Môi trường Python & Venv trên Admin**:
  - Python hệ thống (`AppData\Local\Programs\Python\Python311`) có thể thiếu thư viện.
  - Venv đầy đủ package (`yt-dlp`, `f2`, `onnxruntime`, `openpyxl`, `psutil`):
    `C:\Users\Admin\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`
- **Khởi chạy Tiến trình Ngầm Độc Lập (Detached Process)**:
  - Để tiến trình không bị tắt khi SSH connection đóng lại, dùng PowerShell `Start-Process`:
    ```powershell
    Start-Process -FilePath <python_exe> -ArgumentList @("<script_path>", "<arg1>", "<arg2>") -WorkingDirectory "D:/Taadaa/Tiktok-video" -WindowStyle Hidden
    ```

---

## 3. Chuỗi Render Tự Động Cuốn Chiếu trên Admin (`admin_render_chain.py`)
- **Mục đích**: Tự động render lần lượt qua các slot Tik5 $\rightarrow$ Tik6 $\rightarrow$ Tik7 $\rightarrow$ Tik8 mà không làm nghẽn CPU host Admin (`parallel=1`).
- **Thư mục output**: `D:\TIKTOK-videonuoinick-admin`.
- **Thư mục source**: `D:\video goc may 2`.
- **Lệnh chạy**:
  ```bash
  ssh admin-farm 'powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath python -ArgumentList @(\"D:/Taadaa/Tiktok-video/scripts/admin_render_chain.py\", \"--start-from\", \"5\", \"--skip-wait-tik2\") -WorkingDirectory \"D:/Taadaa/Tiktok-video\" -WindowStyle Hidden"'
  ```
- **File log theo dõi**: `D:\CodexRuntime\tiktok-video\batch-runs\admin_render_chain.log`.

---

## 4. Pipeline Cào Video Gái Xinh (VN + Douyin) trên Admin (`run_admin_gaixinh_downloader.py`)
- **Mục đích**: Quét tự động các folder còn thiếu nguồn ($\le 30$ video) trong `D:\video goc may 2` và kích hoạt tải bù video gái xinh tuyển chọn.
- **Độ ưu tiên dải folder**: Ưu tiên Slot 5..8 (`321..640`) để phục vụ ngay cho chuỗi render đang chạy.
- **Nguồn video**:
  1. Kênh TikTok / YouTube Shorts gái xinh VN tuyển chọn từ `D:\Taadaa\Tiktok-video\data\source_manifest_gaixinh.jsonl`.
  2. Kênh Douyin Hot Girls tuyển chọn từ `D:\Taadaa\Tiktok-video\data\douyin_hot_girls.json` qua tool `f2` (yêu cầu cookie tại `C:\Users\Admin\AppData\Local\hermes\evidence\douyin_test\cookie_string.txt`).
- **File log theo dõi**: `D:\CodexRuntime\tiktok-video\download_gaixinh_admin.log`.

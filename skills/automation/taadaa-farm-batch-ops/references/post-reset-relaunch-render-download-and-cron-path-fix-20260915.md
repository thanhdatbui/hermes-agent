# Triage & Chuẩn Hóa Relaunch Render & Downloader Sau Máy Reset, Fix Path Script Cron Watchdog & Thấu Triệt Nguyên Nhân Thiếu Nguồn

## 1. Hiện Tượng & Ngữ Cảnh Thực Tế (15/09/2026)
1. **User phàn nàn:** *"Clgt nãy h k render k down đc thêm gì cả"*.
   - Tiến trình Render thực tế vẫn chạy bình thường (ffmpeg PID 39480/172092/176552 tăng từ 28 lên 39 video cho folder 384).
   - Tiến trình Downloader đã hoàn tất quét từ folder 481 đến 640 từ ~17:50 và tự động kết thúc do 98 folder còn lại bị chuyển trạng thái `insufficient_pool`.
2. **Sự cố Cron Alert bắn lỗi lúc 20:20:**
   `⚠️ Cron 'post-evening-account-reconcile-watchdog' failed: Script not found: C:\Users\Kibe\AppData\Local\hermes\scripts\watchdog_post_evening_reconcile.py`.
   - User giận dữ: *"Địt cụ mày phá gì thế"*.
3. **User thông báo máy reset:** *"kibe ms bị reset chạy download và render lại đi"*.

## 2. Nguyên Nhân Gốc Rễ (Root Causes)

### A. Sự Cố Cron "Script not found: watchdog_post_evening_reconcile.py"
- Khi tạo cronjob `post-evening-account-reconcile-watchdog` (job_id `1d3035a5fde2`), script được lưu vào thư mục `C:\Users\Kibe\.hermes\scripts\` thay vì thư mục runtime chuẩn của scheduler trên Windows là `C:\Users\Kibe\AppData\Local\hermes\scripts\`.
- Ngoài ra, trong code Python Windows nếu dùng raw string có dấu backslash như `Path(r"D:\Taadaa\runtime\...")` hoặc `Path(r"D:\Taadaa\tools\...")`, ký tự `\r` và `\t` bị hiểu nhầm thành escape characters (`\r` = carriage return, `\t` = tab) làm sai lệch đường dẫn thư mục.

### B. Vấn Đề Thiếu Nguồn Downloader (Insufficient Pool)
- Trong 640 folders: đã có 542 folders đạt $\ge 30$ video. 98 folders còn lại (dải 600..640) bị kẹt `insufficient_pool`.
- **Nguyên nhân kép:**
  1. File pool `sources.qualified30.json` chỉ chứa 506 kênh YouTube, không có kênh TikTok nào (`platform: tiktok` = 0).
  2. Toàn bộ 506 kênh trong pool đã bị claim tới 406 kênh trên `global-ledger` (chia sẻ giữa các máy Admin/Kibe), chỉ còn 100 kênh unclaimed.
  3. Khi chạy lại một folder cụ thể (Canary folder 601 niche Làm đẹp), nếu trong `state.db` folder đã từng bị gán `platform = 'tiktok'`, script ưu tiên platform cũ hoặc cơ chế ratio sẽ bỏ qua nguồn YouTube nếu không ép cờ `--fixed-platform youtube`.

### C. Quản Lý Tiến Trình Nền Khi Máy Bị Reset
- Khi máy Kibe bị restart/reboot, toàn bộ tiến trình render và download nền bị mất.
- Cần khởi chạy lại canonical launcher bằng đúng pattern PowerShell/CMD ngầm, tuyệt đối không tạo subagent ôm batch dài làm timeout.

## 3. Quy Trình Khắc Phục Chuẩn Xác Đã Thực Hiện

### A. Khắc Phục Triệt Để Cron Watchdog
1. Copy và đồng bộ file script về đúng 3 nơi:
   - `C:\Users\Kibe\AppData\Local\hermes\scripts\watchdog_post_evening_reconcile.py`
   - `D:\Taadaa\Hermes\deploy\hermes-home\scripts\watchdog_post_evening_reconcile.py`
   - `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\watchdog_post_evening_reconcile.py`
2. Thay thế toàn bộ dấu `\` thành forward-slash `/` trong code Python (ví dụ: `Path("D:/Taadaa/runtime/kibe/cron-state/...")`).
3. Xác minh qua `cronjob(action='run', job_id='1d3035a5fde2')` xác nhận `execution_success: true`.

### B. Lệnh Chuẩn Relaunch Sau Reset Máy

#### 1. Relaunch Render Slot 7 & Slot 8:
Khởi chạy ngầm độc lập qua PowerShell WindowStyle Hidden:
```powershell
powershell.exe -Command "Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File D:/Taadaa/Tiktok-video/run_kibe_slot7_slot8_render.ps1 -AutoRun' -WorkingDirectory 'D:/Taadaa/Tiktok-video' -WindowStyle Hidden"
```
- Tự động kiểm tra các folder trong `D:\video goc` có $\ge 30$ video và chưa render đủ 30 video trong `D:\TIKTOK-videonuoinick` để tiếp tục render.
- Khởi chạy tiến trình `ffmpeg.exe` mã hóa với 1 worker duy nhất (`--parallel 1`).

#### 2. Relaunch Downloader Phủ Kín Folders:
Khởi chạy ngầm độc lập qua CMD WindowStyle Hidden:
```powershell
powershell.exe -Command "Start-Process cmd -ArgumentList '/c D:\Taadaa\Tiktok-video\run_download_kibe_full.bat' -WorkingDirectory 'D:/Taadaa/Tiktok-video' -WindowStyle Hidden"
```
- Kích hoạt `download_by_niche.py` với 20 workers song song, `--all-languages`, xoay vòng qua 67 cổng proxy live để tiếp tục tải.

#### 3. Xác Minh 3 Tầng Sau Relaunch (Verification Gate):
1. **Kiểm tra Process ID:** `Get-CimInstance Win32_Process` xác nhận có `run_kibe_slot7_slot8_render.ps1`, `random_batch_render.py`, `ffmpeg.exe`, và `download_by_niche.py`.
2. **Kiểm tra Tải CPU & RAM:** `ffmpeg.exe` có WorkingSet $\approx 1.8$ GB, CPU tăng đều; `python.exe` downloader ăn RAM $\approx 98$ MB.
3. **Kiểm tra File Output:** File video `.mp4` mới trong thư mục đích (`D:\TIKTOK-videonuoinick\<folder>`) được tạo với kích thước tăng dần.

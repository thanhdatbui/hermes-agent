# Chẩn Đoán & Khắc Phục Downloader Dừng Do Tràn Ổ Đĩa Farm Admin

1. **Dấu hiệu Nhận Biết**
- Báo cáo định kỳ `farm-render-download-watchdog` ghi nhận:
  - Farm Admin Video gốc (`D:\video goc may 2`): `⚪ Đang dừng`.
  - Số lượng video hoặc folder đạt chuẩn không tăng qua các mốc thời gian (ví dụ kẹt tại 98/640 folder, 9,290 clip).
- Log downloader trên Admin (`D:\CodexRuntime\tiktok-video-machine2\download_admin_p10.log`):
  - Xuất hiện chuỗi liên tục lặp lại mỗi 30s: `download_by_niche exited with code 1. Resting 30s before next scan...`
  - Traceback kết thúc bằng `OSError: [Errno 28] No space left on device` hoặc Python crash khi mở file / ghi video tạm.
- **Triệu chứng Render tưởng chừng không resume sau khi tắt Game:**
  - Watchdog `watchdog_admin_render.py` vẫn spawn worker, nhưng ffmpeg crash ngay trong 1-2 giây với `ERROR: [Errno 28] No space left on device` do đĩa D chạm 0 byte, khiến người dùng lầm tưởng cơ chế Game Guard bị đơ không tự chạy lại.

## 2. Quy trình Kiểm tra O(1) Hiện Trường
1. **Kiểm tra dung lượng đĩa qua `admin_ssh.py`:**
   ```bash
   python D:/Taadaa/tools/admin_ssh.py "python -c \"import shutil; total, used, free = shutil.disk_usage('D:'); print(f'Total: {total//(1024**3)} GB, Used: {used//(1024**3)} GB, Free: {free//(1024**2)} MB')\""
   ```
   Nếu `Free: 0 MB` -> Khẳng định 100% nguyên nhân là tràn ổ đĩa `D:`.

2. **Rà soát các thư mục phình to trên ổ D: Admin:**
   - `D:\TIKTOK-videonuoinick-admin`: Thư mục render thành phẩm (thường chiếm >500 GB do clip render chất lượng cao hoặc clip dư >45/folder).
   - `D:\video goc may 2`: Thư mục video gốc tải về (~160 GB).
   - `D:\x`: Game đang chơi của User (League of Legends / Riot Games ~90 GB) — CẤM TỰ Ý XÓA.
   - `D:\CodexRuntime\tiktok-video-machine2`: Chứa log (`download_admin_p10.log` có thể phình >100 MB).

## 3. Cạm Bẫy Deadlock Google Drive Virtual Mirror (Vì Sao Cron Giải Phóng Đĩa Bị Bất Lực?)
- **Thắc mắc thường gặp:** "Đã có cron `sync_and_clean_gdrive.py` giải phóng video lên Google Drive 5TB, tại sao đĩa vẫn tràn về 0 MB?"
- **Bản chất kỹ thuật (Google Drive Desktop DriveFS Streaming Cache Deadlock):**
  1. Google Drive Desktop mount ổ đĩa ảo `G:` với `ContentCachePath` cấu hình tại `D:\GoogleDriveCache`.
  2. Driver của Google Drive tính toán dung lượng trống khả dụng của ổ ảo `G:` **dựa trên chính dung lượng trống của ổ đĩa chứa thư mục Cache (ổ `D:`)**.
  3. Khi ổ `D:` chạm ngưỡng `Free: 0 MB`, ổ `G:` cũng báo `Free: 0 MB` (dù tài khoản cloud còn hàng TB).
  4. Script `sync_and_clean_gdrive.py` có cơ chế an toàn nghiêm ngặt: **Chỉ xóa video gốc trên `D:` khi file đã được copy nguyên vẹn lên `G:\My Drive\video_goc_backup`**.
  5. Khi ổ `D:` đã đầy 0 MB, lệnh copy/robocopy sang `G:` bị Windows báo lỗi ngay lập tức:
     `OSError: [Errno 28] No space left on device: 'G:\My Drive\video_goc_backup\...'`
  6. **Vòng lặp bế tắc ("Con gà - Quả trứng"):**
     `D:` đầy $\rightarrow$ `G:` báo hết dung lượng $\rightarrow$ Không copy được lên `G:` $\rightarrow$ Script không xóa file nào trên `D:` $\rightarrow$ `D:` vĩnh viễn kẹt ở 0 MB $\rightarrow$ Downloader và mọi tiến trình ghi đều chết đứng.

## 4. Các Phương Án Giải Phóng Dung Lượng & Phá Vỡ Deadlock
1. **Lỗi `p.name in rendered` bỏ sót video thô `> 45`:**
   - Trong script dọn dẹp `sync_and_clean_gdrive.py`, điều kiện `if p.name in rendered and g_p.is_file()` vô tình bỏ sót các video gốc số lớn (từ `46.mp4` đến `65.mp4`) do render chỉ chạy đến clip 45. Các clip này dù đã được `robocopy` đẩy lên GDrive đầy đủ nhưng không bao giờ bị xóa ở local, tích tụ 50–70 GB rác ngầm.
   - **Xử lý nhanh:** Với các folder đã render đủ $\ge 45$ clip, đối soát trực tiếp file `*.mp4` trên GDrive (`$gi.Length -eq $_.Length`), nếu khớp kích thước thì xóa thẳng local không cần qua robocopy hay lọc `p.name in rendered`:
     ```powershell
     Get-ChildItem "D:\video goc may 2" -Directory | ForEach-Object { $f = [int]$_.Name; $slot = [math]::Floor(($f - 1)/80) + 1; $m = (($f - 1) % 80) + 1; $f_vid = ($m - 1)*8 + $slot; $r = "D:\TIKTOK-videonuoinick-admin\$f_vid"; if (Test-Path $r) { $rendCount = (Get-ChildItem $r -Filter "*.mp4").Count; if ($rendCount -ge 45) { $g = "G:\My Drive\video_goc_backup\$($_.Name)"; if (Test-Path $g) { Get-ChildItem $_.FullName -Filter "*.mp4" | ForEach-Object { $gp = "$g\$($_.Name)"; if (Test-Path $gp) { $gi = Get-Item $gp; if ($gi.Length -eq $_.Length) { Remove-Item $_.FullName -Force } } } } } } }
     ```
2. **Chiến lược Phân tầng Kho Render (Tiered Render Storage - Giữ 1..20, Đẩy 21..45 lên Cloud):**
   - Kho `D:\TIKTOK-videonuoinick-admin` chiếm hơn 620 GB. Do farm chỉ upload 1 clip/ngày và các máy hiện mới ở clip 1..6 (tối đa 10), các clip từ 21..45 phải 1-2 tháng nữa mới dùng đến.
   - Đẩy các clip từ `21.mp4..45.mp4` lên `G:\My Drive\video_render_backup\{f_vid}` và giữ lại `1.mp4..20.mp4` tại local giải phóng ngay 300–350 GB đĩa D mà không làm gián đoạn upload của farm.
3. **Khóa tạm Downloader bằng cờ Pause Flag:**
   - Task Scheduler trên Admin có task `Taadaa_Admin_Downloader_15m` tự động khởi động lại downloader 40 luồng mỗi 15 phút. Nếu chỉ kill tiến trình, nó sẽ tự spawn lại và tiếp tục đổ video làm tràn đĩa.
   - BẮT BUỘC đặt cờ `C:\Users\Admin\downloader_pause.flag` và bọc kiểm tra ở đầu `main()` trong `run_admin_downloader_service.py` để thoát ngay trong 0.5s (`[PAUSED] Downloader paused via flag.`).
4. **Phục hồi Video Gốc Bị Đẩy Sớm Từ GDrive (Cho Folders Render < 45):**
   - Ánh xạ ngược từ thư mục render sang thư mục nguồn:
     `slot = (f_vid - 1) % 8 + 1`, `m_idx = (f_vid - 1) // 8 + 1`, `f_src = (slot - 1) * 80 + m_idx`.
   - Nếu `D:\TIKTOK-videonuoinick-admin\{f_vid}` có `< 45` clip và nguồn local bị thiếu, copy ngược từ `G:\My Drive\video_goc_backup\{f_src}` về `D:\video goc may 2\{f_src}` để worker render đủ chuẩn $\ge 45$.
5. **Kích Hoạt Nền Dài Hạn Qua OpenSSH Bắt Buộc Dùng Breakaway (`0x01000008`):**
   - Khi kích hoạt migration hoặc sync script kéo dài > 5 phút qua SSH, Windows OpenSSH mặc định gom process con vào Windows Job Object của phiên SSH và kill sạch khi SSH disconnect.
   - BẮT BUỘC dùng cờ `creationflags=0x01000008` (`CREATE_BREAKAWAY_FROM_JOB | DETACHED_PROCESS`) và mở log ở chế độ binary `open(log_p, "ab")`.
   - Bọc fallback `psutil` bằng lệnh chuẩn Windows `tasklist` vì Python hệ thống (`Python311`) có thể không có sẵn package `psutil` (chỉ có trong `venv-core024`).
6. **Mồi dung lượng trống khẩn cấp (Bootstrap Free Space):**
   - Google Drive và cron dọn dẹp cần tối thiểu 20–30 GB đệm trên ổ `D:` để ghi cache tạm khi upload.
   - Cắt tỉa clip render dư thừa (`> 45` clip/folder trong `D:\TIKTOK-videonuoinick-admin`), dọn dẹp video gốc đã được đồng bộ an toàn lên Cloud, hoặc truncate log nặng. TUYỆT ĐỐI CẤM tự tiện xóa thư mục game `D:\x` của User.
   - Ngay khi `D:` có dung lượng trống, ổ `G:` sẽ tự động mở lại dung lượng ghi, `sync_and_clean_gdrive.py` sẽ hoạt động trơn tru trở lại.
6. **Cắt tỉa clip render dư thừa:** Giữ tối đa 45 clip/folder trong `D:\TIKTOK-videonuoinick-admin`, xóa các clip từ `46.mp4` trở lên.
7. **Truncate log:** Truncate các file log quá nặng trong `CodexRuntime` (`download_admin_p10.log`).
8. **Kỷ luật Giám sát & Ngưỡng An Toàn (Safety Headroom Invariant):**
   - Downloader trên Admin cần cơ chế dừng mềm / cảnh báo khi `FreeSpace(D:) < 30 GB` thay vì để tải kiệt quệ về 0 MB làm sập chuỗi tự động dọn dẹp.

## 5. Tái Khởi Động Downloader Sau Khi Có Dung Lượng Trống
- Chạy script launch detached downloader qua SSH:
  ```bash
  python D:/Taadaa/tools/launch_admin_downloader.py
  ```
- Kiểm tra tiến trình `python.exe` / `pythonw.exe` xuất hiện lại trong `tasklist` của Admin.

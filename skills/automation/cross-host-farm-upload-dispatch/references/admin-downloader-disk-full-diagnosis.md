# Chẩn Đoán & Khắc Phục Downloader Dừng Do Tràn Ổ Đĩa Farm Admin

## 1. Dấu hiệu Nhận Biết
- Báo cáo định kỳ `farm-render-download-watchdog` ghi nhận:
  - Farm Admin Video gốc (`D:\video goc may 2`): `⚪ Đang dừng`.
  - Số lượng video hoặc folder đạt chuẩn không tăng qua các mốc thời gian (ví dụ kẹt tại 98/640 folder, 9,290 clip).
- Log downloader trên Admin (`D:\CodexRuntime\tiktok-video-machine2\download_admin_p10.log`):
  - Xuất hiện chuỗi liên tục lặp lại mỗi 30s: `download_by_niche exited with code 1. Resting 30s before next scan...`
  - Traceback kết thúc bằng `OSError: [Errno 28] No space left on device` hoặc Python crash khi mở file / ghi video tạm.

## 2. Quy trình Kiểm tra O(1) Hiện Trường
1. **Kiểm tra dung lượng đĩa qua `admin_ssh.py`:**
   ```bash
   python D:/Taadaa/tools/admin_ssh.py "python -c \"import shutil; total, used, free = shutil.disk_usage('D:'); print(f'Total: {total//(1024**3)} GB, Used: {used//(1024**3)} GB, Free: {free//(1024**2)} MB')\""
   ```
   Nếu `Free: 0 MB` -> Khẳng định 100% nguyên nhân là tràn ổ đĩa `D:`.

2. **Rà soát các thư mục phình to trên ổ D: Admin:**
   - `D:\TIKTOK-videonuoinick-admin`: Thư mục render thành phẩm (thường chiếm >500 GB do clip render chất lượng cao hoặc clip dư >45/folder).
   - `D:\video goc may 2`: Thư mục video gốc tải về (~160 GB).
   - `D:\x`: Chứa game / installer cũ (như League of Legends / Riot Games ~90 GB).
   - `D:\CodexRuntime\tiktok-video-machine2`: Chứa log (`download_admin_p10.log` có thể phình >100 MB).

## 3. Các Phương Án Giải Phóng Dung Lượng An Toàn
1. **Xóa các installer / game rác không dùng (`D:\x`):** Giải phóng ngay ~90 GB mà không ảnh hưởng tới dữ liệu farm.
2. **Cắt tỉa clip render dư thừa:** Giữ tối đa 45 clip/folder trong `D:\TIKTOK-videonuoinick-admin`, xóa các clip từ `46.mp4` trở lên.
3. **Truncate log:** Truncate các file log quá nặng trong `CodexRuntime`.

## 4. Tái Khởi Động Downloader Sau Khi Có Dung Lượng Trống
- Chạy script launch detached downloader qua SSH:
  ```bash
  python D:/Taadaa/tools/launch_admin_downloader.py
  ```
- Kiểm tra tiến trình `python.exe` / `pythonw.exe` xuất hiện lại trong `tasklist` của Admin.

# Troubleshooting & Chuẩn Hóa Downloader Sau Khi Máy Bị Reset, Proxy DNS & Cron Script Path

## 1. Sự Cố Phát Sinh Khi Kibe Reset Hoặc Cron Lỗi (15/09/2026)

### A. Cron Script Lưu Sai Thư Mục Gây Báo Động Hàng Loạt
- **Hiện tượng**: Cronjob `post-evening-account-reconcile-watchdog` (job_id `1d3035a5fde2`) báo lỗi định kỳ:
  `Script not found: C:\Users\Kibe\AppData\Local\hermes\scripts\watchdog_post_evening_reconcile.py`.
- **Nguyên nhân**: Script được ghi vào `C:\Users\Kibe\.hermes\scripts\` thay vì `C:\Users\Kibe\AppData\Local\hermes\scripts\` (thư mục runtime chuẩn của Hermes trên Windows host này).
- **Khắc phục**:
  - Luôn ghi script cron vào `C:\Users\Kibe\AppData\Local\hermes\scripts\`.
  - Đồng bộ sang `D:\Taadaa\Hermes\deploy\hermes-home\scripts\` và `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\`.
  - Dùng forward-slash `/` hoặc raw string trong path Python để tránh escape sequence (`\r`, `\t`, `\b`).

### B. Proxy DNS Lỗi Phân Giải Tên Miền Gây 100% Download Thất Bại
- **Hiện tượng**: `download_by_niche.py` ném hàng loạt lỗi:
  `NameResolutionError("HTTPSConnection(host='test.taadaa.click', port=5114): Failed to resolve 'test.taadaa.click' ([Errno 11001] getaddrinfo failed)")`.
- **Nguyên nhân**: DNS resolver trên Windows hoặc mạng nội bộ chập chờn không phân giải được domain `test.taadaa.click` hoặc `mirotik1.taadaa.click`.
- **Khắc phục**:
  - Thay thế trực tiếp domain bằng IP đích đã resolve sẵn:
    - `test.taadaa.click` -> `116.107.115.121`
    - `mirotik1.taadaa.click` -> `192.168.110.2`
  - Tạo file proxy riêng `proxy_pool_67_direct.txt` để bypass hoàn toàn DNS lookups khi chạy yt-dlp/downloader.

### C. Lỗi Cú Pháp File `.bat` Khi Cắt Dòng Bằng `^`
- **Hiện tượng**: Chạy `run_download_kibe_full.bat` bị lỗi `The filename, directory name, or volume label syntax is incorrect`.
- **Nguyên nhân**: File batch Windows khi cắt dòng nhiều tham số bằng dấu `^` rất dễ bị lỗi syntax do khoảng trắng hoặc ký tự xuống dòng LF/CRLF.
- **Khắc phục**:
  - Chuẩn hóa launcher sang file PowerShell script `.ps1` (`run_download_kibe.ps1`) với mảng tham số `$argsList = @(...)` và gọi `& $python @argsList`.
  - Khởi chạy nền không chiếm cửa sổ:
    ```powershell
    Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File D:/Taadaa/Tiktok-video/run_download_kibe.ps1' -WorkingDirectory 'D:/Taadaa/Tiktok-video' -WindowStyle Hidden
    ```

### D. Cơ Chế Nhận Diện Nguồn Thiếu Do Platform Fallback
- **Hiện tượng**: Trong pool có 506 nguồn YouTube nhưng downloader báo `INSUFFICIENT_POOL` vì chọn platform `tiktok` (pool tiktok hiện tại = 0 nguồn).
- **Khắc phục**:
  - Khi kho nguồn chỉ gồm YouTube Shorts, thêm cờ cứng `--fixed-platform youtube` vào lệnh chạy để ép downloader quét 100% nguồn YouTube có sẵn.

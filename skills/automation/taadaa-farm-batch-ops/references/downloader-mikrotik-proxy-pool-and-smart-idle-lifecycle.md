# Downloader Proxy Pool (MikroTik vs Direct) & Smart Idle Lifecycle

## 1. Bẫy Cào Video Bằng Direct Proxy & Nguy Cơ Lỗi Ngầm Không Báo Cáo
- **Hiện tượng & Nhầm lẫn phổ biến**:
  - Người vận hành hoặc script cũ có xu hướng hardcode `--proxy-pool proxy_pool_67_direct.txt` (dải MobiProxy `test.taadaa.click:51xx`).
  - Khi thấy tiến trình downloader vẫn có PID trong `psutil`/`tasklist`, người ta ngộ nhận là "cào bằng direct vẫn được".
  - **Thực tế hiện trường**:
    + Các cổng MobiProxy đặt tại mạng ngoài (Thái Bình), thường xuyên bị botnet quét, rate-limit hoặc ngắt kết nối tạm thời.
    + Khi request tải video qua Mobi direct bị lỗi (HTTP 429, 502, connection reset, timeout), `yt-dlp` và `download_by_niche.py` bắt ngoại lệ để thử lại hoặc skip sang video/kênh khác mà **KHÔNG ném fatal error ra ngoài console** và **KHÔNG gửi alert về Telegram**.
    + Hệ quả: Tiến trình vẫn sống nhưng thực chất đang rơi vào vòng lặp trượt liên tục (skip hàng loạt candidates, cạn kiệt pool), tải cực kỳ chậm hoặc đứng im, gây thiếu hụt video nghiêm trọng trên farm mà không ai hay biết.

- **Dải 69 Proxy MikroTik (`proxy_pool_69.txt` / `proxy_pool_67.txt`)**:
  - Gồm 69 line trỏ vào `mirotik1.taadaa.click:10001..10035` (`admin@1:admin@1`).
  - File `C:\Windows\System32\drivers\etc\hosts` trên máy farm đã map `mirotik1.taadaa.click -> 192.168.110.2`.
  - Kết nối nội bộ qua router MikroTik RouterOS (35 line PPPoE quay số độc lập) với độ trễ cực thấp (<0.2s), không phụ thuộc vào đường truyền WAN bên ngoài và không bị firewall bên thứ 3 drop gói.
  - **Quy tắc bất biến**:
    * Mọi script cào (`run_kibe_downloader_service.py`, `run_admin_downloader_service.py`, `auto_rescan_loop.py`, `run_admin_foreground_loop.py`) **BẮT BUỘC phải trỏ vào `proxy_pool_69.txt`** (hoặc pool gộp `proxy_pool_full_all.txt` ưu tiên MikroTik).
    * CẤM TUYỆT ĐỐI cấu hình direct-only (`proxy_pool_67_direct.txt`).

## 2. Kiến Trúc Smart Idle 2 Tầng Cho Cào Và Render Toàn Farm
Hệ thống vận hành theo cơ chế tự ngắt khi đủ và tự phục hồi khi thiếu:

### Tầng 1: Worker Nặng (CPU / RAM / Disk I/O)
- **Downloader Service (`run_kibe_downloader_service.py` / `run_admin_downloader_service.py`)**:
  - Sử dụng file lock `msvcrt` (`admin_downloader.lock` / `kibe_downloader.lock`) chống chạy trùng tiến trình.
  - Quét thực tế trên đĩa (không tin DB đơn lẻ) toàn bộ 640 folder (`1..640`):
    * Kibe: `D:\video goc`
    * Admin: `D:\video goc may 2`
  - Điều kiện dừng: Khi **tất cả 640/640 folder** đều đạt $\ge 45$ clip `.mp4`, worker tự động ghi log `[ALL_COMPLETE]` và thoát hẳn (`sys.exit(0)`), giải phóng 100% tài nguyên máy.
- **Render Worker (`run_kibe_render_worker.py` / `run_admin_render_worker.py`)**:
  - Tuân thủ quy chuẩn render 1 worker (`--parallel 1`) để không nghẽn CPU.
  - Mapping chéo theo đúng 8 file Excel (`Tik1.xlsx` .. `Tik8.xlsx`).
  - Chỉ render khi `source_count >= 30 and source_count > output_count`. Khi không còn folder nào thỏa mãn, worker tự động thoát.

### Tầng 2: Watchdog Nhẹ & Silent (Hermes Cron & Startup VBS)
- **Hermes Cronjob (Chu kỳ 15 phút, `no_agent: true`)**:
  - `kibe-downloader-watchdog` & `admin-downloader-watchdog`
  - `kibe-render-worker-watchdog` & `admin-render-worker-watchdog`
  - Logic kiểm tra nhanh (<0.05s):
    1. Kiểm tra nếu kho đã đủ 640 folder $\ge 45$ clip $\rightarrow$ thoát ngay.
    2. Kiểm tra nếu tiến trình worker đang chạy (`psutil`) $\rightarrow$ thoát ngay.
    3. Giữ `stdout` rỗng tuyệt đối để không spam thông báo lên Telegram.
    4. Chỉ khi phát hiện thiếu video (do farm tiêu hao clip đăng bài) và chưa có worker chạy $\rightarrow$ spawn worker chạy ngầm (`CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS`).
- **Sống sót qua Reboot (Windows Startup)**:
  - File `.vbs` đặt trong `shell:startup` (`AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\`):
    * `start_kibe_downloader_watchdog.vbs` & `start_kibe_render_watchdog.vbs` trên Kibe.
    * `start_downloader_watchdog.vbs` & `start_render_watchdog.vbs` trên Admin.
  - Sau khi máy reboot (nhờ `AutoAdminLogon = 1`), VBS tự động gọi pythonw chạy watchdog ngầm, kết hợp lock `msvcrt` để không xung đột với Cronjob.

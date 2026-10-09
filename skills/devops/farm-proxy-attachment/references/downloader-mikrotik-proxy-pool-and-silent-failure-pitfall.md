# Bẫy Cào Video Bằng Proxy Direct & Kiến Trúc Pool 69 MikroTik Downloader

## 1. Sự Cố "Cào Bằng Direct Vẫn Được Nhưng Thực Chất Lỗi Ngầm Không Báo"
- **Nguyên nhân gốc rễ**:
  * Khi script cào (`download_by_niche.py`, `auto_rescan_loop.py`, `run_admin_foreground_loop.py`) bị cấu hình nhầm sang dải direct MobiProxy `proxy_pool_67_direct.txt` (các cổng `test.taadaa.click:51xx`):
  * Dải MobiProxy nằm tại Thái Bình qua mạng WAN ngoài, thường xuyên bị bot scan, rate-limit bởi CDN TikTok/YouTube, hoặc sập cổng 51xx.
  * Khi request tải video hoặc trích xuất metadata bị lỗi (429, 502, timeout, reset), `yt-dlp` và `download_by_niche.py` bắt ngoại lệ để skip video/kênh mà **KHÔNG ném fatal exception** và **KHÔNG gửi cảnh báo về Telegram**.
  * Hậu quả: Tiến trình vẫn hiển thị PID trong `psutil`/`tasklist`, người vận hành tưởng "direct vẫn chạy được", nhưng thực chất downloader trượt liên tục, cào cực kỳ chậm hoặc đứng im, gây thiếu hụt video nghiêm trọng trên farm.

## 2. Ưu Thế Tuyệt Đối Của Pool 69 Proxy MikroTik (`proxy_pool_69.txt` / `proxy_pool_67.txt`)
- Gồm 69 line trỏ vào `mirotik1.taadaa.click:10001..10035` (`admin@1:admin@1`).
- Domain `mirotik1.taadaa.click` đã được map thẳng vào IP LAN `192.168.110.2` trong `hosts`.
- Kết nối nội bộ qua router MikroTik RouterOS (35 line PPPoE quay số độc lập) với độ trễ cực thấp (<0.2s), không phụ thuộc vào đường truyền WAN ngoài và không bị firewall cản trở.
- **Quy tắc bất biến**:
  * Mọi script cào trên cả Kibe và Admin **BẮT BUỘC phải trỏ vào `proxy_pool_69.txt`** (hoặc pool gộp `proxy_pool_full_all.txt` ưu tiên MikroTik).
  * CẤM TUYỆT ĐỐI cấu hình direct-only (`proxy_pool_67_direct.txt`).

## 3. Kiến Trúc Smart Idle Cho Downloader Toàn Farm
- **Service persistent (`run_kibe_downloader_service.py` / `run_admin_downloader_service.py`)**:
  * Khóa bằng `msvcrt` file lock chống chạy trùng.
  * Quét thực tế trên đĩa (không tin DB đơn lẻ) 640 folder (`1..640`): Kibe `D:\video goc`, Admin `D:\video goc may 2`.
  * Khi đủ 640/640 folder $\ge 45$ clip $\rightarrow$ tự động dừng hẳn (`sys.exit(0)`), giải phóng 100% tài nguyên CPU/RAM/băng thông.
- **Watchdog 15p (Hermes Cron & Windows Startup VBS)**:
  * Kiểm tra nhanh: nếu đã đủ 640 folder hoặc service đang chạy $\rightarrow$ im lặng tuyệt đối (`stdout` rỗng, CPU 0%).
  * Nếu phát hiện thiếu video và chưa có service $\rightarrow$ spawn service chạy ngầm.

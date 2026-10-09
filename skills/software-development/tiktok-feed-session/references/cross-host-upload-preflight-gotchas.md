# Cross-Host Feed & Upload Preflight Gotchas (Central Controller vs Remote Cluster)

## Bối cảnh & Hiện tượng (Session 2026-10-05)
- Hệ thống Phone Farm chạy theo kiến trúc **Central Controller (máy Kibe điều khiển toàn bộ Farm gồm cụm Kibe M1-80 và cụm Admin M201-280 qua ADB socket TCP `192.168.110.119:5037`)**.
- Watchdog Telegram (`feed_session_watchdog.py`) báo alert:
  `• Đăng Video: + Hết video/Cần cào (41): 201, 203, 204, ...`
- Kiểm tra thực tế trên host Admin (`admin-farm`):
  - Kho `D:\TIKTOK-videonuoinick-admin` đã có hơn 27.500 video render hoàn tất (Tik1 đạt 97.5% folder >= 45 clip).
  - Tất cả các video mục tiêu (`1/3.mp4`, `17/3.mp4`, `25/2.mp4`...) đều tồn tại thật 100% trên ổ D: của máy Admin (`Test-Path` trả về `True`).

## Nguyên nhân cốt lõi (Root Cause)
1. **Lệch môi trường kiểm tra tệp (Filesystem Locality Mismatch):**
   - Runner `tiktok_runner.py` chạy trên máy Kibe gọi `multi_machine_feed_session.py` với `$env:TAADAA_HOST_CONFIG = "admin.yaml"`.
   - File cấu hình `admin.yaml` chỉ định `media_source_root = D:\TIKTOK-videonuoinick-admin`.
   - Tuy nhiên, tiến trình Python thực thi Gate 5 (`upload_preflight.py` / `_run_upload_hook()`) chạy trên CPU máy Kibe. Khi gọi `video_file.is_file()`, nó kiểm tra đường dẫn local `D:\TIKTOK-videonuoinick-admin` trên ổ đĩa của **Kibe**, thay vì máy **Admin**.
   - Vì máy Kibe không có thư mục này (hoặc chưa map SMB share `\\admin-farm\TIKTOK-videonuoinick-admin`), Python kết luận file không tồn tại -> gán `reason: "video_not_rendered"`.
2. **Watchdog hiểu nhầm lỗi:**
   - `feed_session_watchdog.py` duyệt thấy `reason: "video_not_rendered"` nên tự động gom vào nhóm `Hết video/Cần cào`, gây hoang mang cho người vận hành rằng farm đang thiếu video dù kho video thực tế đã render đầy đủ.

## Quy tắc xử lý & Phòng ngừa (Invariant)
1. **Tuyệt đối không kết luận thiếu video chỉ dựa vào watchdog text:**
   - Luôn SSH vào host remote (`ssh admin-farm`) kiểm tra thực tế bằng lệnh nhanh O(1) (`farm_render_download_watchdog.py` hoặc PowerShell `Test-Path`).
2. **Xử lý kiến trúc Central Controller:**
   - Hoặc chia sẻ thư mục mạng SMB từ Admin (`D:\TIKTOK-videonuoinick-admin` chia sẻ thành `\\192.168.110.119\TIKTOK-videonuoinick-admin` và cấu hình `media_source_root` dạng UNC path).
   - Hoặc ủy quyền việc upload hook chạy trực tiếp trên host sở hữu thiết bị và media qua remote executor thay vì kiểm tra tệp local trên Controller.

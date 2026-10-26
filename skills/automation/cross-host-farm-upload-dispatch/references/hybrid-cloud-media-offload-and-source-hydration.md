# Hybrid Cloud Media Offload & Source Hydration Protocol (Taadaa Farm)

## 1. Bối cảnh & Vấn đề Cốt lõi
Trên máy chủ Farm Admin (M201–M280):
- Ổ cứng `D:` có dung lượng 1.000 GB, nhưng thư mục render thành phẩm `D:\TIKTOK-videonuoinick-admin` phình to tới >620 GB (hơn 24.000 clip).
- Downloader tải liên tục video gốc (~200 GB) kết hợp với các bản cài đặt game/tools khiến ổ đĩa dễ dàng chạm ngưỡng 0 MB trống (`[Errno 28] No space left on device`).
- Khi ổ `D:` về 0 MB, ổ ảo Google Drive `G:` (do đặt cache trên `D:\GoogleDriveCache`) cũng bị Windows khóa ghi, gây ra Deadlock: Cron không thể copy sang `G:` nên không xóa được file trên `D:`.

## 2. Chiến lược Phân tầng Lưu trữ (Hybrid Cache Tiering)
Điện thoại farm đăng tối đa 1 video/ngày. Với 640 tài khoản:
- Tuyệt đối không giữ toàn bộ 45–65 clip render/folder trên ổ SSD local.
- **Tầng Local (`D:\TIKTOK-videonuoinick-admin\{f_vid}`):** Chỉ giữ các clip từ `1.mp4` đến `20.mp4` (đủ gối đầu cho farm hoạt động liên tục 20 ngày mà không cần mạng).
- **Tầng Cloud (`G:\My Drive\video_render_backup\{f_vid}`):** Đẩy toàn bộ các clip $\ge 21$ (`21.mp4` đến `45.mp4`+) lên Google Drive 5TB.

### Quy tắc Offload an toàn:
1. Chỉ xóa file local khi file trên Google Drive đã tồn tại và khớp chính xác dung lượng byte-for-byte.
2. Kiểm tra Game Guard (`war3`, `tft`, `league of legends`) trước khi thực hiện để không gây nghẽn I/O khi User chơi game.
3. Giải phóng ngay lập tức ~350 GB – 400 GB dung lượng trống trên ổ SSD!

## 3. Quy tắc Tính toán & Phục hồi Video Gốc Bị Xóa Oan (JIT Source Hydration)
Khi cần khôi phục video gốc từ `G:\My Drive\video_goc_backup` về local `D:\video goc may 2` để render tiếp cho các folder dở dang:
- **TỬ HUYỆT CẦN TRÁNH:** Không được kiểm tra `len(local_rendered) < 45` đơn thuần! Vì các folder đã offload lên Cloud chỉ còn 20 clip local, nếu chỉ đếm local sẽ bị ngộ nhận là thiếu và kéo nhầm hàng chục GB video gốc đã render xong về máy.
- **CÔNG THỨC CHUẨN XÁC:**
  $$\text{Total Rendered} = \text{Count}(\text{Local Rendered}) + \text{Count}(\text{GDrive Render Backup})$$
- **Quy tắc kích hoạt:**
  - Nếu $\text{Total Rendered} \ge 45$: Folder đã hoàn thành 100%, BỎ QUA, tuyệt đối không phục hồi video gốc.
  - Nếu $\text{Total Rendered} < 45$: Folder thực sự còn dở dang, tìm `f_src = (slot - 1)*80 + m_idx` và kéo các clip gốc còn thiếu từ `G:\My Drive\video_goc_backup\{f_src}` về `D:\video goc may 2\{f_src}`.

## 4. Trình tự Xử lý Chống Tràn Đĩa Tái Diễn (Strict Sequence)
1. **Bước 1 (Khóa Downloader):** Tạo cờ `C:\Users\Admin\downloader_pause.flag` để ngăn Task Scheduler tự spawn `download_by_niche.py` cào bừa làm tràn đĩa.
2. **Bước 2 (Offload Render High Numbers):** Chạy offload các clip $\ge 21$ lên Google Drive trước để đưa dung lượng trống từ 30 GB lên >150–200 GB.
3. **Bước 3 (Restore Incomplete Sources):** Kéo các video gốc của những folder thực sự `< 45` clips về local. Do đĩa đã có >150 GB trống nên việc kéo ~34 GB nguồn về hoàn toàn an toàn, không có nguy cơ chạm ngưỡng 0 MB.
4. **Bước 4 (Resume Render 2 Workers):** Bật lại `run_admin_render_worker.py` với 2 luồng ffmpeg song song để hoàn tất các folder dở dang.

## 5. Quy chuẩn Triển khai Service Nền qua OpenSSH Windows
- Script chạy nền dài hạn trên Admin bắt buộc tách Job Object bằng `creationflags = 0x01000008` (`CREATE_BREAKAWAY_FROM_JOB | DETACHED_PROCESS`).
- Môi trường Python hệ thống trên Admin (`Python311`) có thể thiếu `psutil`: bắt buộc bọc `try...except ImportError` và fallback sang lệnh hệ thống `tasklist` của Windows.

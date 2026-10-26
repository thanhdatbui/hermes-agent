# Chiến Lược Phân Tầng Media Render (Rendered Video Tiering & GDrive Staging)

## 1. Bối Cảnh & Vấn Đề
- Trên máy chủ Farm Admin (quản lý 80 máy M201–M280):
  - Dung lượng ổ `D:` là 931 GB.
  - Thư mục thành phẩm render `D:\TIKTOK-videonuoinick-admin` chứa 640 folder nuôi nick (80 máy x 8 slot), khi đạt chuẩn $\ge 45$ clip/folder sẽ phình to tới **>625 GB**, chiếm gần 70% toàn bộ dung lượng ổ đĩa.
  - Khi cộng thêm video gốc (`D:\video goc may 2` ~160–200 GB) và game Riot PBE (~90 GB), ổ `D:` lập tức chạm ngưỡng **Free: 0 MB**.
  - Khi `D:` chạm 0 MB, FFmpeg và toàn bộ tiến trình ghi văng lỗi `[Errno 28] No space left on device`, làm tê liệt toàn bộ dây chuyền render.

## 2. Nghịch Lý Lệch Pha Giữa Render và Tốc Độ Nuôi Nick
- Tốc độ render: Worker có thể render 50–100 clip/ngày.
- Tốc độ đăng bài của Phone Farm: Mỗi máy chỉ đăng **1 clip / ngày** (hoặc cách ngày).
- Qua đối soát thực tế sổ cái `taikhoan_run_safe.xlsx`:
  - 483 / 640 tài khoản mới đăng `0 clip`.
  - Toàn bộ cụm Admin mới đăng tối đa đến clip số **4**.
  - Các clip render số lớn từ **`21.mp4` đến `45.mp4`** (hơn 15.000 video, chiếm ~350–400 GB) phải **tối thiểu 16–20 ngày đến 2 tháng nữa** farm mới cần dùng tới!
  - Việc giữ chết 350–400 GB video số lớn trên ổ SSD là nguyên nhân cốt tử gây tràn đĩa.

## 3. Kiến Trúc Phân Tầng Hybrid (Local Buffer + Cloud Cold Staging)
Hệ thống chia kho video thành phẩm làm 2 tầng:

1. **Local Hot Buffer (`D:\TIKTOK-videonuoinick-admin`):**
   - Chỉ lưu trữ các clip từ **`1.mp4` đến `20.mp4`** cho mỗi folder.
   - 20 clip là đủ gối đầu cho toàn bộ farm đăng bài an toàn suốt 20 ngày mà hoàn toàn không phụ thuộc mạng.

2. **Cloud Cold Staging (`G:\My Drive\video_render_backup`):**
   - Đẩy toàn bộ các clip từ **`21.mp4` trở lên** lên Google Drive 5TB.
   - **Quy tắc nghiệm thu an toàn (Byte-for-byte Verify):** Từng file chỉ được phép xóa khỏi local `D:\` khi và chỉ khi file trên `G:\My Drive\video_render_backup` tồn tại và khớp chính xác 100% dung lượng byte.
   - **Hiệu quả:** Giải phóng ngay lập tức **~350 GB đến 400 GB dung lượng trống** trên ổ D!

3. **Cơ Chế Kéo Về Tự Động (JIT Hydrate):**
   - Khi một tài khoản trên điện thoại đăng chạm ngưỡng clip số **15**, cron helper tự động kéo trước batch tiếp theo (21–30) từ Google Drive về local trong vài giây qua mạng Internet.

## 4. Quy Trình Vận Hành 2 Pha Độc Lập
*Lưu ý invariant:* Bắt buộc thông báo trước thời gian ước tính (khoảng 15–20 phút cho ~450 folders) trước khi kích hoạt dịch vụ offload diện rộng ngầm để tránh người dùng hiểu lầm tiến trình bị treo.

Script điều phối chuẩn `C:\Users\Admin\manage_admin_media_gdrive.py` (hoặc launcher nền `run_media_migration_service.py`):

1. **Pha 1 (Offload):**
   ```bash
   python C:/Users/Admin/manage_admin_media_gdrive.py offload 640
   ```
   Quét 640 folder, đẩy clip $\ge 21$ lên Google Drive, verify byte match và xóa local để tạo ngay ~350 GB trống.

2. **Pha 2 (Restore Source cho Folder dở dang):**
   ```bash
   python C:/Users/Admin/manage_admin_media_gdrive.py restore 640
   ```
   Rà soát các folder có `< 45` clip render, tra cứu `f_src = (slot - 1)*80 + m_idx`, kéo video gốc bị đẩy lên Drive oan về `D:\video goc may 2` để render worker render đủ chuẩn 45 clip.

## 5. Kỷ Luật Khóa Downloader Khi Ổ Đĩa Cần Ưu Tiên Render
- Để tránh Downloader 40 luồng tự động cào video mới làm tràn ổ đĩa trở lại:
  - Tạo cờ `C:\Users\Admin\downloader_pause.flag`.
  - Trong `run_admin_downloader_service.py`, hàm `main()` bắt buộc kiểm tra:
    ```python
    if os.path.exists(r"C:\Users\Admin\downloader_pause.flag"):
        print("[PAUSED] Downloader paused via flag.")
        sys.exit(0)
    ```
  - Khi cần kích hoạt lại downloader: chỉ cần xóa file flag này.

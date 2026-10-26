# Farm Admin Tiered Storage Management & Source Recovery Protocol

## 1. Bối Cảnh & Vấn Đề
- Ổ đĩa `D:` trên Farm Admin (M201-280) có dung lượng 931 GB.
- Thư mục thành phẩm render `D:\TIKTOK-videonuoinick-admin` khi render đủ 640 folder có thể phình tới >620 GB (hơn 15.000 clips).
- Đồng thời kho video gốc `D:\video goc may 2` chiếm ~200 GB.
- Hệ quả: Ổ `D:` liên tục cạn kiệt về `0 MB`, dẫn tới Google Drive Desktop stream cache (`D:\GoogleDriveCache`) bị khóa ghi `Errno 28`, gây tê liệt cả tiến trình Render và Downloader.

## 2. Chiến Lược Phân Tầng Hybrid Storage (Offload Clips >= 21 Lên Google Drive)
- **Đặc thù nghiệp vụ:**
  - Thiết bị điện thoại farm chỉ đăng 1 clip/ngày. Toàn bộ 80 máy Admin mới chỉ đăng đến clip số 1–6 (tối đa clip 4).
  - Các clip số lớn (`21.mp4` đến `45.mp4`) phải 2–3 tuần nữa máy mới dùng tới.
- **Quy tắc phân tầng:**
  - **Local (`D:\TIKTOK-videonuoinick-admin`):** Giữ lại từ `1.mp4` đến `20.mp4` (đủ gối đầu cho farm chạy liên tục 20 ngày).
  - **Google Drive (`G:\My Drive\video_render_backup\{f_vid}`):** Đẩy toàn bộ các clip $\ge 21$ lên Cloud.
  - **Invariant Byte-for-byte:** Bắt buộc kiểm tra `gdrive_file.size == local_file.size` trước khi thực hiện `unlink()` file local.
- **Hiệu quả:** Giải phóng tức thì ~350 GB đến 400 GB dung lượng trống trên ổ `D:`.

## 3. Quy Trình Khóa Tạm Downloader Bằng Cờ (`downloader_pause.flag`)
- Task Scheduler trên Admin có các task chạy định kỳ (`Taadaa_Admin_Downloader_15m`).
- Để ngăn downloader liên tục cào video gốc mới làm tràn đĩa mà không cần đụng quyền quản trị Task Scheduler:
  - Tạo file cờ: `C:\Users\Admin\downloader_pause.flag`.
  - Trong `run_admin_downloader_service.py`, đặt kiểm tra ngay đầu `main()`:
    ```python
    if os.path.exists(r"C:\Users\Admin\downloader_pause.flag"):
        print("[PAUSED] Downloader paused via flag.")
        sys.exit(0)
    ```
  - Khi cần resume, chỉ cần xóa file flag.

## 4. Cạm Bẫy Đếm Clip Thành Phẩm Khi Tải Bù Nguồn Gốc (False Deficit Trap)
- **Bẫy phát hiện:** Khi kiểm tra xem folder nào cần kéo video gốc về để render bù:
  - Nếu chỉ đếm file local: `len(list(r_dir.glob("*.mp4"))) < 45`, các folder đã offload clip $\ge 21$ lên GDrive sẽ chỉ còn 20 clip local và bị ngộ nhận là chưa render xong, dẫn đến việc kéo thừa hàng chục GB video gốc về đĩa!
- **Invariant tính tổng thành phẩm:**
  ```python
  local_rend = len([p for p in r_dir.glob("*.mp4") if p.stat().st_size > 100000]) if r_dir.is_dir() else 0
  gdrive_rend_dir = GDRIVE_RENDER_BACKUP / str(f_vid)
  gdrive_rend = len([p for p in gdrive_rend_dir.glob("*.mp4") if p.stat().st_size > 100000]) if gdrive_rend_dir.is_dir() else 0
  total_rend = local_rend + gdrive_rend

  if total_rend < 45:
      # CHỈ kéo video gốc cho các folder có tổng thành phẩm thực sự < 45
      restore_source_from_gdrive(f_src)
  ```

## 5. Quy Chuẩn Khởi Chạy Nền Không Phụ Thuộc (Breakaway & No psutil)
- **Môi trường Python:** Môi trường Python hệ thống trên Admin (`C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe`) có thể thiếu `psutil`. Bắt buộc bọc `try...except ImportError` và fallback sang `tasklist /fo csv` qua `subprocess`.
- **Windows OpenSSH Disconnect Trap:** Kích hoạt tiến trình nền dài hạn qua `admin_ssh.py` bắt buộc dùng cờ `creationflags=0x01000008` (`CREATE_BREAKAWAY_FROM_JOB | DETACHED_PROCESS`) để không bị kill khi phiên SSH đóng.

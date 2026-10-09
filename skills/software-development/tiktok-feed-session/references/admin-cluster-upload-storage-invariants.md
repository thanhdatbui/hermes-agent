# Admin Cluster Upload & Storage Invariants (Dual-Farm Architecture)

## 1. Hiện trạng Kiến trúc Farm 160 máy
- **Cụm Kibe (Máy 1–80):** Cắm USB trực tiếp vào máy Kibe (local ADB). Kho video tại `D:\TIKTOK-videonuoinick`.
- **Cụm Admin (Máy 201–280):** Cắm vào máy Admin (`192.168.110.119`), điều khiển qua ADB socket `tcp:192.168.110.119:5037`. Kho video tại `D:\TIKTOK-videonuoinick-admin` trên ổ đĩa máy Admin.
- **Single Controller Model:** Máy Kibe là controller duy nhất điều phối cả 2 cụm theo lịch Cron.

## 2. Bẫy lỗi nghiêm trọng: Kiểm tra nhầm ổ đĩa (Cross-host Path Checking)
- **Hiện tượng:** Watchdog báo động giả `Hết video/Cần cào (42)` cho toàn bộ máy Farm Admin dù kho Admin có hơn 27.500 video sẵn sàng.
- **Nguyên nhân gốc rễ:** 
  - Runner chạy trên CPU máy Kibe. 
  - Tại Gate 5 của `_run_upload_hook()` trong `multi_machine_feed_session.py`, code kiểm tra:
    ```python
    video_file = media_root / folder_video / f"{next_video}.mp4"
    if not video_file.is_file() or video_file.stat().st_size == 0:
        return {"status": "skipped", "reason": "video_not_rendered"}
    ```
  - Với máy Admin (`machine >= 200`), `media_root` là `D:\TIKTOK-videonuoinick-admin`. Nhưng thư mục này nằm trên máy Admin, KHÔNG TỒN TẠI trên ổ D của Kibe.
  - Python trên Kibe kiểm tra local thấy không có file -> đánh dấu `video_not_rendered` trên hàng loạt máy.

## 3. Quy tắc Bất biến (Hard Invariants)
1. **CẤM đề xuất share thư mục qua SMB/LAN:** User cực kỳ dị ứng việc share thư mục hay kéo kho video giữa 2 máy. Bộ não điều phối chỉ phát lệnh, storage ở đâu thì node đó tự xử lý.
2. **Quyền sở hữu Storage (Storage Ownership):**
   - Với máy Kibe (1–80): Kiểm tra file và chạy subprocess local trên Kibe.
   - Với máy Admin (201–280): BỎ QUA kiểm tra file local trên Kibe (`is_file()` / `stat()`).
   - Kibe dispatch lệnh qua SSH sang máy Admin:
     ```bash
     ssh admin-farm "powershell -Command \"cd D:/Taadaa/Tiktok-video; & 'D:/Taadaa/python-envs/automation/Scripts/python.exe' -m scripts.tiktok_workflow --config D:/Taadaa/Tiktok-video/config-admin.yaml --workflow-workbook D:/OneDrive/TaadaaData/admin/Tik<N>.xlsx --single-device <serial> --video-number <num> --video-source-root D:/TIKTOK-videonuoinick-admin --allow-device-reboot-recovery --no-dry-run\""
     ```
   - Máy Admin tự kiểm tra file trên ổ D của nó và tự push video vào điện thoại.
3. **Audit Trail & Git Closeout:** Khi sửa luồng upload hook cho máy Admin, bắt buộc chạy focused test (`test_upload_hook.py`), chạy Canary trên 1 máy thật (ví dụ Máy 201), và hoàn tất Closeout Gate để commit/push lên `master`. Tuyệt đối không để uncommitted diff bị trôi dạt sang session khác.

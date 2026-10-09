# Xử lý mâu thuẫn: Watchdog Render báo xong 100% nhưng Script Upload báo thiếu video (VIDEO_FILE_MISSING)

## 1. Hiện tượng
- Watchdog render (`farm_render_download_watchdog.py` hoặc `tikX_render_watchdog.py`) báo cáo:
  `✅ TikX: 80/80 folder (≥30 clip) [100.0%]`
- Nhưng khi khởi chạy script upload (`run_tiktok_upload_batch.ps1` / `run_post.py` / `tiktok_workflow`), hàng loạt máy bị văng lỗi ngay bước chuẩn bị video:
  `VIDEO_FILE_MISSING` hoặc `PathResolverError: Video file not found: D:\TIKTOK-videonuoinick\<Folder Video>\<N>.mp4`

## 2. Bản chất kỹ thuật & Cơ chế mâu thuẫn
1. **Tiêu chí của Watchdog Render**:
   - Hàm đếm trong watchdog chỉ kiểm tra: `count = sum(1 for f in os.listdir(folder) if f.endswith('.mp4')) >= 30`.
   - Watchdog **không quan tâm tên file là gì hay có bắt đầu từ 1.mp4 hay không**. Chỉ cần trong thư mục có đủ $\ge 30$ file MP4 là đánh dấu hoàn tất.
2. **Tiêu chí của Script Upload (`path_resolver.py`)**:
   - Khi chuẩn bị đăng clip, `path_resolver.resolve_video_path` tìm chính xác file theo công thức:
     `video_path = media_source_root / str(folder_video) / f"{int(video_da_dang) + 1}.mp4"`
   - Với nick chưa từng đăng (`Video Đã Đăng = 0`), script **bắt buộc tìm đúng file `1.mp4`**.
   - Với nick đã đăng 1 clip (`Video Đã Đăng = 1`), script **bắt buộc tìm đúng file `2.mp4`**.
3. **Nguyên nhân gây lệch**:
   - Quá trình render từ nguồn `D:\video goc` chọn lọc danh sách clip ngẫu nhiên (ví dụ bốc từ file 18 đến 64 để render đủ 45 video).
   - Render script (`random_batch_render.py`) giữ nguyên số thứ tự nguồn thay vì renumber tuần tự từ 1 $\rightarrow$ Trong output folder chỉ có `18.mp4 .. 64.mp4`, hoàn toàn không có `1.mp4`.
   - Kết quả: Thư mục có đủ 45 clip render nhưng script upload không thể lấy được `1.mp4` để đăng.

## 3. Quy trình khắc phục chuẩn (Không render lại)
1. **Kiểm tra hiện trạng numbering**:
   ```python
   import os, re
   # Quét folder xem có bắt đầu từ 1.mp4 và liên tục hay không
   ```
2. **Renumber tuần tự**:
   - Chạy script chuẩn hóa sắp xếp các file MP4 hiện có theo thứ tự tăng dần và đổi tên thành `1.mp4, 2.mp4, ..., N.mp4`.
   - Giữ nguyên chất lượng video đã render, không đốt CPU render lại từ đầu.
3. **Đồng bộ Workbook `TikX.xlsx`**:
   - Cập nhật `Render Status = OK` và `Render MP4 = <số lượng file>` cho toàn bộ 80 máy.

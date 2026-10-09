# Chẩn đoán & Khắc phục Mâu thuẫn Render Xong nhưng Báo "Chưa render/thiếu video"

## 1. Hiện tượng & Nghịch lý Chẩn đoán (The Paradox)
- **Bên Render báo**: Đã hoàn tất 100% (`80/80 folder đạt ≥30 video`, tổng 3.000+ video MP4). Watchdog render báo tick xanh `✅`.
- **Bên Watchdog Feed / Hook Upload báo**:
  ```text
  • Đăng Video:
    + Bỏ qua: Chưa render/thiếu video (N máy)
  ```
  hoặc runner văng lỗi:
  ```text
  PathResolverError: Video file not found: D:\TIKTOK-videonuoinick\<folder>\<K>.mp4
  ```
  hoặc `VIDEO_FILE_MISSING`.

---

## 2. Nguyên nhân Gốc rễ (Root Cause)
1. **Lệch quy ước đặt tên file giữa Render và Upload**:
   - Tool render (`random_batch_render.py`) khi lấy mẫu clip từ `D:\video goc\<folder>` (ví dụ lấy 45 clip ngẫu nhiên từ 65 clip nguồn) đã giữ nguyên tên gốc của file nguồn (`relative_source.with_suffix(".mp4")`).
   - Nếu các clip được chọn là `18.mp4, 19.mp4, ..., 64.mp4`, thì thư mục thành phẩm `D:\TIKTOK-videonuoinick\<folder>` có đủ 45 video nhưng **bắt đầu từ 18.mp4**, hoàn toàn KHÔNG có `1.mp4`.
2. **Cơ chế tìm file của Upload Pipeline (`path_resolver.py`)**:
   - Luồng upload xác định file cần đăng tiếp theo dựa trên cột `Video Đã Đăng` trong file Excel:
     $$\text{Target MP4} = (\text{Video Đã Đăng} + 1)\text{.mp4}$$
   - Nick mới (`Video Đã Đăng = 0`) $\rightarrow$ Bắt buộc tìm `1.mp4`.
   - Nick đã đăng 1 clip (`Video Đã Đăng = 1`) $\rightarrow$ Bắt buộc tìm `2.mp4`.
   - Khi folder không có file `(Video Đã Đăng + 1).mp4`, `resolve_video_path()` ném `PathResolverError`, hook bắt được lý do `video_not_rendered` / `missing_video_folder` $\rightarrow$ Watchdog kết luận nhầm là **"Chưa render/thiếu video"** dù folder có thừa video.

---

## 3. Bản vá Chuẩn hóa cho Render Pipeline (`random_batch_render.py`)
Tại hàm `make_tasks`, file output phải luôn được gán theo số thứ tự task (`seq = 1..N`):
```python
# CHUẨN ĐÃ VÁ:
for seq, source in enumerate(videos, 1):
    relative_source = source.relative_to(input_dir)
    # Ép tên file đích luôn tuần tự 1.mp4, 2.mp4, ... N.mp4
    relative_output = relative_source.parent / f"{seq}.mp4"
    output = output_root / relative_output
    ...
```
Và trong `render_one`:
```python
relative_output = task.relative_output
```

---

## 4. Kỷ luật An toàn Tuyệt đối khi Renumber Chuẩn hóa Folder Cũ
Khi gặp các folder đã render từ trước bị đánh số không tuần tự (ví dụ folder bắt đầu từ `18.mp4` hoặc bị khuyết số ở giữa):
1. **INVARIANT BẢO TOÀN VIDEO ĐÃ ĐĂNG**:
   - Đọc giá trị `posted = int(row['Video Đã Đăng'] or 0)` từ workbook.
   - **CẤM TUYỆT ĐỐI**: Đổi tên, di chuyển hoặc ghi đè lên các file từ `1.mp4` đến `posted.mp4`. Đây là các video đã thực sự đăng lên kênh TikTok của thiết bị thật; nếu đổi tên sẽ làm lệch hoàn toàn lịch sử và đối soát video fingerprint.
2. **CƠ CHẾ RENAME 2 BƯỚC (TWO-PHASE TEMP RENAME)**:
   - Gom toàn bộ các file còn lại (chưa đăng), sắp xếp theo thứ tự số tăng dần.
   - Đổi tên toàn bộ sang file tạm `.tmp_renumber_{idx}.mp4` để tránh trường hợp số mới trùng số cũ gây đè chéo (Collision).
   - Đổi tên từ file tạm sang file đích tuần tự: `(posted + 1).mp4`, `(posted + 2).mp4`, ... đến hết.
3. **ĐỒNG BỘ EXCEL `TikX.xlsx`**:
   - Cập nhật cột `Render Status = 'OK'`.
   - Cập nhật cột `Render MP4 = len(mp4_files)`.
   - Sử dụng cơ chế ghi an toàn (atomic write + backup `.bak`).

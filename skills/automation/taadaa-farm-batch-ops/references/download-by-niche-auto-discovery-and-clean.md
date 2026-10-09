# Download By Niche: Auto-Discovery & Incomplete Folder Clean Contract

## 1. Cơ chế Auto-Discovery Nguồn Video (download_by_niche.py)

Khi một folder cần tải nhưng pool nguồn hiện tại (cả platform chính lẫn platform fallback) không có kênh nào đạt số lượng video tối thiểu:
- Trước khi chuyển trạng thái folder sang `insufficient_pool`, script gọi `auto_discover_niche_source()`.
- **Query tìm kiếm**:
  - `ytsearch15:{niche.label} shorts việt nam`
  - `ytsearch10:{niche.label} shorts`
- **Bộ lọc**:
  - Bỏ qua kênh đã tồn tại trong local `sources` hoặc trong `global_ledger_dir`.
  - Bỏ qua kênh nằm trong danh sách loại trừ (`exclusions`).
  - Probe kênh qua URL shorts (`.../shorts`) để kiểm tra số lượng video hợp lệ `>= min_videos`.
- **Tích hợp & Persistence**:
  - Tự động claim nguồn mới vào `global_ledger_dir` theo máy (`ledger_machine_id` / `COMPUTERNAME`).
  - Ghi bổ sung kênh vào `sources.json` / `sources.jsonl`.
  - Nạp inline vào `option_candidates` và kiểm tra qua language gate / niche filter; nếu đủ `>= min_videos` thì gán nguồn và tiến hành tải hoàn thiện folder.

## 2. Kỷ luật Dọn dẹp Folder Dở dang (`clean_incomplete_folder_and_db`)

### Nguy cơ:
Nếu folder tải chưa đủ số lượng `min_videos` mà bị dừng/lỗi, các video đã tải nằm lại trong thư mục. Lần sau nếu gán một kênh khác vào folder đó, folder sẽ bị **trộn 2 kênh nội dung khác nhau** (rác metadata, avatar sai lệch, nội dung không đồng nhất).

### Quy chuẩn xử lý khi folder không đạt `min_videos`:
Hàm `clean_incomplete_folder_and_db(folder_num, output_dir, args)` được kích hoạt trước khi cập nhật trạng thái lỗi:
1. **Dọn sạch file trong output_dir**:
   - Quét và `unlink()` tất cả các file: `*.mp4`, `*.part`, `*.part.mp4`, `*.jpg`, `*.json`.
2. **Dọn sạch DB state**:
   - `DELETE FROM videos WHERE folder=?`
   - `UPDATE folders SET status='insufficient_pool', source_channel=NULL, video_count=0 WHERE folder_num=?`
3. **Log chuẩn hóa**:
   - Ghi ra stderr: `INSUFFICIENT_POOL_CLEANED folder={folder_num} videos_deleted={count} required={args.min_videos}`.

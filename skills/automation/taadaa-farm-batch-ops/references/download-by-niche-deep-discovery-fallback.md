# Deep Discovery & Niche Fallback trong download_by_niche.py (Taadaa Farm)

## Bối cảnh & Nguyên nhân dừng sớm
Khi chạy batch tải video (`download_by_niche.py`), các folder thường bị dừng hoặc chuyển trạng thái `insufficient_pool` sớm do:
1. Nguồn trong pool có ít hơn `min_videos` (mặc định 30 Shorts).
2. Sau `max_attempts` (mặc định 3 attempts), script dừng vòng lặp và đánh dấu `insufficient_pool` mà chưa vét các ngách dồi dào khác.
3. Cơ chế `auto_discover_niche_source` ban đầu chỉ quét trong đúng ngách được giao, khi ngách đó hiếm kênh tiếng Việt đủ 30 shorts thì tự động trả về `None`.

## Chuẩn thiết kế Auto-Discovery & Niche Fallback (2026-09-19)

### 1. Niche Fallback List (Ngách dồi dào nhất)
Khi ngách hiện tại hết nguồn đạt chuẩn, downloader tự động duyệt qua danh sách ngách dự phòng:
```python
FALLBACK_NICHES = (
    "cuoi",
    "amthuc",
    "review",
    "khampha",
    "phim",
    "meovat",
    "tintuc",
    "congnghe",
)
```

### 2. Cập nhật state.db & Log chuẩn
Khi phát hiện kênh phù hợp từ ngách thay thế:
- Cập nhật trường `niche` trong bảng `folders` của `state.db`.
- Log chuẩn format để monitor và báo cáo:
  `NICHE_FALLBACK folder={folder_num} from={old_niche} to={new_niche}`

### 3. Vòng lặp run_folder & Quy tắc dừng
- Khi `attempt >= max_attempts` mà vẫn chưa đạt `min_videos`:
  - Thực hiện một lượt deep discovery với danh sách ngách fallback.
  - Nếu tìm được nguồn mới thỏa mãn `>= min_videos`, tiếp tục tải ngay và hoàn thành folder.
  - Chỉ khi cả ngách gốc và toàn bộ ngách thay thế đều cạn kiệt nguồn, mới đánh dấu `insufficient_pool`.

### 4. Quy tắc cô lập Folder (1 folder = 1 kênh)
- Bất cứ khi nào đổi nguồn thất bại hoặc chuyển sang ngách mới:
  - Bắt buộc gọi `clean_incomplete_folder_and_db(folder_num, output_dir, args)`.
  - Xóa toàn bộ file dở dang (`.mp4`, `.jpg`, `.json`) trong thư mục folder.
  - Đánh dấu các video cũ trong DB là `source_incomplete` và reset `video_count=0`.

# Downloader: Multi-Source Retry, Inline Auto-Discovery & Incomplete Folder Cleanup

Tài liệu thiết kế và xử lý xung đột / tích hợp cho `scripts/download_by_niche.py` trong repo `D:\Taadaa\Tiktok-video`.

---

## 1. Kiến trúc luồng Multi-Source Retry & Auto-Discovery

Khi tải video theo niche cho từng folder (`run_folder`):
1. **Outer Retry Loop**: `while attempt < max_attempts:` (mặc định 3 attempts).
2. **Platform & Source Search**:
   - Duyệt qua danh sách `platform_order` (`requested_platform`, rồi các platform fallback).
   - Lọc các nguồn phù hợp từ DB/file cấu hình (`eligible_sources`), loại bỏ các `tried_source_urls`.
   - Nếu tìm thấy nguồn có đủ `>= min_videos` ứng viên hợp lệ (vượt qua popularity gate, language gate, exclusion list), chọn nguồn đó làm `source`.
3. **Inline Auto-Discovery Fallback (Khi local pool cạn nguồn)**:
   - Nếu `not source`: Thử gọi `auto_discover_niche_source(folder_num, niche, args, sources, exclusions, verified, report)`.
   - Nếu tìm thấy kênh đạt `>= min_videos`:
     - Gán `source = option`, `candidates = option_candidates`, `platform = "youtube"`.
   - Nếu vẫn `not source`:
     - Fallback gọi `source_pool_builder` (`discover_web("tiktok", ...)` hoặc `discover_youtube(...)`).
     - Thêm các nguồn mới tìm được vào `sources` pool và `continue` sang attempt tiếp theo.

---

## 2. Incomplete Folder Cleanup (`clean_incomplete_folder_and_db`)

### Vấn đề:
Nếu một folder tải dở dang từ nguồn A (chưa đủ `min_videos`, ví dụ mới được 15/30 video), khi script retry nguồn B, nếu không dọn dẹp sẽ dẫn tới **1 folder bị trộn lẫn video của 2 kênh khác nhau**.

### Cơ chế dọn dẹp chuẩn:
Hàm `clean_incomplete_folder_and_db(folder_num: int, output_dir: Path, args: argparse.Namespace) -> int`:
1. Xóa toàn bộ file media dở dang trong folder:
   - Patterns: `*.mp4`, `*.part`, `*.part.mp4`, `*.jpg`, `*.json`.
2. Dọn sạch DB state:
   - `DELETE FROM videos WHERE folder=?`
   - `conn.commit()`
3. Cập nhật trạng thái folder khi kiệt sức (exhausted attempts):
   - `UPDATE folders SET status='insufficient_pool', source_channel=NULL, video_count=0 WHERE folder_num=?`
   - Ghi báo cáo `write_report` với `status="insufficient_pool"`, `rejection_reason="no_source_with_minimum_candidates"`.
   - In log chuẩn: `INSUFFICIENT_POOL folder=...`

---

## 3. Quy trình Kiểm thử & Xác thực

Trước khi commit bất kỳ thay đổi nào liên quan đến retry/cleanup:
1. **Compile check**:
   ```bash
   python -m py_compile scripts/download_by_niche.py
   ```
2. **Unit test retry & qualification**:
   ```bash
   pytest tests/test_source_retry.py -v
   pytest tests/test_vietnamese_pipeline.py -v
   ```

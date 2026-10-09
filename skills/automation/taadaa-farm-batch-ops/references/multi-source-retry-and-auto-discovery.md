# Multi-Source Retry & Auto-Discovery in download_by_niche.py (2026-09-18)

## 1. Vấn đề giải quyết
- Trước đây khi một kênh (source) trong pool chỉ tải được một vài video hoặc ít hơn `min_videos` (ví dụ: yêu cầu 30-45 videos nhưng kênh chỉ có 15 video tải thành công), folder bị bỏ dở hoặc bị ghi đè lẫn lộn giữa các kênh.
- Nếu nguồn trong pool cạn, batch download dừng hoặc đánh dấu `insufficient_pool`.

## 2. Kiến trúc giải pháp (Case 102 + Inline Auto-Discovery)
1. **Multi-Source Retry Loop (`--max-source-attempts`, mặc định 3)**:
   - Thử tuần tự các source hợp lệ trong pool (ưu tiên source cũ của folder nếu hợp lệ).
   - Nếu source tải xong nhưng số lượng video đạt chuẩn `< min_videos`:
     - Kích hoạt `clean_incomplete_folder_and_db(folder_num, output_dir, args)`:
       - Xóa sạch file media dở dang (`*.mp4`, `*.part*`, `*.jpg`, `*.json`) khỏi output directory.
       - Xóa record videos trong SQLite `state.db` tương ứng với folder đó.
     - Reset trạng thái folder: `UPDATE folders SET status='pending', source_channel=NULL, video_count=0 WHERE folder_num=?`.
     - Chuyển sang thử source kế tiếp trong danh sách (`tried_source_urls`).

2. **Inline Auto-Discovery Fallback (`auto_discover_niche_source`)**:
   - Khi đã thử hết các source trong pool mà vẫn không có source đạt `>= min_videos`:
   - Tự động chạy search YouTube Shorts:
     - `ytsearch15:<niche.label> shorts việt nam`
     - `ytsearch10:<niche.label> shorts`
   - Kiểm tra `existing_keys` và `global_ledger_dir` để tránh trùng lặp kênh máy khác đang dùng.
   - Probe kênh mới: nếu số video shorts hợp lệ `>= min_videos`:
     - Claim vào global ledger (`claim_source`).
     - Lưu kênh mới vào file `sources.json` / `sources.jsonl`.
     - Sử dụng ngay kênh này để download cho folder hiện tại.

## 3. Pitfall khi Test & Xác thực
- Trên môi trường Windows / Taadaa farm repo, thư mục `.pytest_cache` có thể bị lock quyền (`Permission denied: .pytest_cache`).
- Khi chạy pytest xác thực cho downloader, luôn chỉ định thư mục cache tạm hoặc tắt cacheprovider:
  ```bash
  python -m pytest tests/test_source_retry.py -o cache_dir=/tmp/pytest_cache
  # hoặc
  python -m pytest tests/test_source_retry.py -p no:cacheprovider
  ```

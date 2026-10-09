# Auto-Discovery Khi Thiếu Nguồn (Insufficient Pool) & Đối Soát Trạng Thái state.db Chống Trộn Kênh

## 1. Ngữ cảnh & Vấn đề
Trong pipeline tải video theo niche (`download_by_niche.py`) trên máy farm (Kibe/Admin):
- **Hiện tượng**: Khi hết các kênh đã quét trong `sources.qualified*.json`, downloader gặp folder thiếu nguồn sẽ rơi vào `INSUFFICIENT_POOL`, cập nhật `folders.status = 'insufficient_pool'` và dừng hoặc skip.
- **Nguy cơ trộn kênh (Channel Cross-Contamination)**:
  - Một folder video TikTok chỉ được phép chứa video từ **DUY NHẤT 1 KÊNH** nguồn (1-to-1 mapping), không bao giờ được trộn video từ nhiều kênh vào cùng 1 folder.
  - Khi một folder đã tải dở (ví dụ 10-25 video) nhưng thiếu video và bị đánh dấu `failed` với `rejection_reason='download_no_media'`, việc tự động auto-discover và cắm kênh mới vào folder đó sẽ làm **trộn 2 kênh vào cùng 1 folder**, phá vỡ tính nhất quán của nick TikTok.

## 2. Quy tắc đối soát an toàn trong `state.db` & Kỷ luật Dọn sạch Folder không đạt chuẩn (Clean-on-Insufficient)
Khi xử lý các folder bị dính `insufficient_pool` hoặc tải dở không đạt chuẩn (< min_videos, mặc định 30 clip):

### A. Kỷ luật Bất biến: Tự động Auto-Discovery, CẤM dừng hỏi
- Khi pool nguồn (`sources.qualified*.json`) hết kênh cho một niche, downloader BẮT BUỘC tự động kích hoạt inline `auto_discover_niche_source` để tìm kiếm kênh YouTube Shorts mới đạt chuẩn $\ge 30$ video và tải tiếp.
- **Tuyệt đối CẤM tự ý kết thúc rồi dừng lại hỏi user** khi chưa quét auto-discovery.

### B. Kỷ luật Dọn sạch Folder không đạt chuẩn (Chống trộn 2 kênh / 1 folder)
- Nếu một folder đã tải dở nhưng kênh nguồn bị cạn clip, không thể đạt đủ số lượng video tối thiểu ($\text{count} < args.min\_videos$):
  - **BẮT BUỘC XÓA SẠCH TOÀN BỘ CLIPS CŨ**: Gọi `clean_incomplete_folder_and_db(folder_num, output_dir, args)` để xóa toàn bộ file `.mp4`, `.part`, `.jpg` đã tải dở trong thư mục của folder trên đĩa (`D:\video goc\<folder_num>`).
  - **DỌN SẠCH RECORD SQLITE**: Xóa sạch toàn bộ các dòng thuộc folder đó trong bảng `videos`:
    ```sql
    DELETE FROM videos WHERE folder = <folder_num>;
    ```
  - **RESET TRẠNG THÁI FOLDER VỀ RỖNG**:
    ```sql
    UPDATE folders 
    SET status = 'insufficient_pool', source_channel = NULL, video_count = 0 
    WHERE folder_num = <folder_num>;
    ```
  - **Mục tiêu**: Tuyệt đối không để sót bất kỳ clip nào của kênh cũ, đảm bảo khi auto-discovery cắm kênh mới vào sẽ là folder 100% thuần khiết từ 1 kênh duy nhất.

### C. Khử spam Telegram từ cronjob (Kỷ luật no_agent: true)
- Với các cronjob dạng script chạy nền (`no_agent: true`, ví dụ `cron_clear_tiktok_cache.py`), cơ chế scheduler tự động tóm mọi output xuất ra `stdout` gửi tin nhắn lên kênh Telegram.
- **Quy tắc bắt buộc**: 
  - Không `print` lỗi kết nối tạm thời (ADB timeout, network busy) ra `stdout`. Phải ghi ra `sys.stderr.write(...)` để giữ tiến trình im lặng khi chạy bình thường.
  - Bọc retry ngắn (e.g. 2 lần kèm `time.sleep(2)`) khi gọi các lệnh hệ thống dễ nghẽn tạm thời như `adb devices`.

## 3. Kiến trúc Auto-Discovery Inline trong `download_by_niche.py`
Để tránh việc batch bị dừng do hết nguồn, hàm Auto-Discovery được kích hoạt tại đúng anchor:
```python
# Ngay trước khối "if not source:" (khoảng dòng 1466 của scripts/download_by_niche.py)
```

### Nguyên tắc thiết kế hàm `auto_discover_niche_source`:
1. **Target Search**:
   - Dùng `yt_dlp.YoutubeDL` tìm kiếm shorts theo từ khóa tiếng Việt của niche:
     - `ytsearch15:{niche.label} shorts việt nam`
     - `ytsearch10:{niche.label} shorts`
2. **Khóa chống trùng (Deduplication & Global Ledger Gate)**:
   - Chuẩn hóa URL kênh bằng `source_key(url)` (từ `global_ledger.py`).
   - Bỏ qua các kênh:
     - Đã có trong danh sách `sources` hiện tại của phiên chạy.
     - Đã được claim bởi máy khác trong ledger JSONL (`read_source_keys(args.global_ledger_dir)`).
3. **Thẩm định kênh (Qualification Gate)**:
   - Quét tab `/shorts` của kênh ứng viên.
   - Thẩm định từng candidate qua:
     - `make_candidate(info, option, niche, verified)`
     - `candidate_passes_language_source_gate(candidate, args)`
     - `text_has_exclusion(candidate_text, exclusions)`
4. **Ngưỡng chấp nhận (Acceptance Threshold)**:
   - Nếu tìm thấy kênh có số candidate đạt chuẩn $\ge args.min\_videos$ (mặc định 30):
     - Tạo đối tượng `Source` hoàn chỉnh với đầy đủ thông tin:
       ```python
       new_source = Source(
           url=channel_url,
           platform="youtube",
           niches=(niche.slug,),
           verified_vn=True,
           uploader=channel_title,
           video_urls=tuple(c.url for c in valid_candidates),
       )
       ```
     - Ghi nhận vào memory `sources.append(new_source)` và append an toàn vào file `args.sources`.
     - Claim nguồn trong `global_ledger` nếu không phải `dry_run`.
     - Lưu candidates vào SQLite `state.db` qua `insert_discovered`.
     - Gán `source = new_source`, `candidates = valid_candidates` để folder tiếp tục tải ngay lập tức.

## 4. Tọa độ Code Anchors & Triển khai cụ thể trong `download_by_niche.py` (Khảo sát 2026-09-18)

### A. Anchor 1: Trước `def run_folder` (khoảng dòng 1309)
Đặt 2 hàm tiện ích:
1. `clean_incomplete_folder_and_db(folder_num: int, output_dir: Path, args: argparse.Namespace) -> int`:
   - Unlink file `.mp4`, `.part`, `.part.mp4`, `.jpg`, `.json` trong `output_dir`.
   - SQLite: `DELETE FROM videos WHERE folder=?` kèm `_DB_LOCK`.
2. `auto_discover_niche_source(folder_num: int, niche: Niche, args: argparse.Namespace, sources: list[Source], exclusions: set[str], verified: dict[str, dict], report: Path) -> Source | None`:
   - **Tuyệt đối không hardcode đường dẫn Windows**: Dùng `target_dir = getattr(args, "cookies_dir", None) or getattr(args, "runtime", None)` và `glob.glob(str(Path(target_dir) / "youtube-cookies*.txt"))`.
   - yt_dlp search shorts: `ytsearch15:{niche.label} shorts việt nam`, `ytsearch10:{niche.label} shorts`.
   - Lọc bỏ channel đã có trong `sources` và ledger (`read_source_keys`).
   - Probe `/shorts`, nếu $\ge args.min\_videos$ candidates đạt chuẩn:
     + Khởi tạo `Source(url=c_url, platform='youtube', niches=(niche.slug,), verified_vn=True, uploader=...)`.
     + Atomic append vào `args.sources` (.tmp + replace) trong `with _DB_LOCK:`.
     + `claim_source(Path(args.global_ledger_dir), machine_id, new_source.url, folder_num)`.
     + Append vào memory `sources.append(new_source)` và trả về `new_source`.

### B. Anchor 2: Ngay trước `if not source:` (khoảng dòng 1467)
```python
    if not source:
        try:
            disc_source = auto_discover_niche_source(
                folder_num, niche, args, sources, exclusions, verified, report
            )
            if disc_source:
                print(f"AUTO_DISCOVERED_SUCCESS folder={folder_num} source={disc_source.url}")
                option = disc_source
                option_candidates = []
                popularity_samples = []
                with yt_dlp.YoutubeDL(yt_options(args, flat=False)) as metadata_ydl:
                    discovered_items = discover_source(option, args)
                    for item in discovered_items:
                        info = item.get("pre_info") or full_info_with_ydl(metadata_ydl, item["url"])
                        if not info:
                            continue
                        candidate = make_candidate(info, option, niche, verified)
                        if not candidate or not candidate_passes_language_source_gate(candidate, args):
                            continue
                        if text_has_exclusion(" ".join([candidate.title, candidate.description, *candidate.tags]), exclusions):
                            continue
                        popularity_samples.append(candidate)
                        if len(option_candidates) < args.max_videos:
                            with _DB_LOCK:
                                conn = connect_state(args.state_db)
                                try:
                                    if insert_discovered(conn, candidate):
                                        option_candidates.append(candidate)
                                finally:
                                    conn.close()
                if len(option_candidates) >= args.min_videos:
                    source = option
                    candidates = option_candidates
                    platform = "youtube"
        except Exception as exc:
            print(f"AUTO_DISCOVER_ERROR folder={folder_num}: {exc}", file=sys.stderr)
    if not source:
```

### C. Anchor 3: Xử lý dọn sạch khi không đạt min_videos (khoảng dòng 1619)
```python
    # Folder không đủ chuẩn min_videos: Xóa sạch media dở dang và giải phóng record DB để bảo đảm an toàn 1 folder 1 kênh
    clean_incomplete_folder_and_db(folder_num, output_dir, args)
    with _DB_LOCK:
        conn = connect_state(args.state_db)
        try:
            conn.execute("UPDATE folders SET status='insufficient_pool',source_channel=NULL,video_count=0 WHERE folder_num=?", (folder_num,))
        finally:
            conn.close()
    print(f"INSUFFICIENT_POOL_CLEANED folder={folder_num} videos_deleted={count} required={args.min_videos}", file=sys.stderr)
    return False
```

### D. Focused Unit Test Contract (`tests/test_auto_discovery_and_clean.py`)
- Test chạy dưới 15-20 giây, không gọi mạng thực tế (mock `yt_dlp.YoutubeDL`).
- Ca 1: `test_clean_incomplete_folder_and_db` — verify file `.mp4`, `.part`, `.jpg`, `.json` bị xoá sạch và record trong bảng `videos` bị xóa.
- Ca 2: `test_auto_discover_niche_source_none` — verify khi search không ra kênh nào đạt min_videos thì trả về `None`.
- Ca 3: `test_auto_discover_niche_source_success` — mock YouTube search trả về kênh $\ge 30$ shorts, verify tạo `Source`, atomic write `sources` file, append `sources` list.


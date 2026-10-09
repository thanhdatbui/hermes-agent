# Tối Ưu SQLite State DB (Tránh Tranh Chấp I/O Ổ HDD) & Cơ Chế Xoay Proxy Tức Thì Khi Download

## 1. Sự cố Nghẽn Cổ Chai I/O Đĩa Cứng Trên `state.db` (12/09/2026)
### Hiện tượng
Khi chạy song song 20 worker download (`download_by_niche.py`) và 1 worker render FFmpeg (`random_batch_render.py`):
- Tiến trình download bị chững lại, số folder hoàn tất đứng yên ở 23/40 suốt nhiều giờ dù mạng và proxy vẫn sống.
- Kiểm tra các worker Python nhận thấy tiến trình kẹt cứng ở các lệnh truy vấn SQLite trên file `D:/CodexRuntime/tiktok-video/state.db`.

### Nguyên nhân kỹ thuật
1. **Tranh chấp I/O đĩa cơ HDD (Drive `D:`)**:
   - Ổ `D:` là ổ đĩa cơ 4TB đang phải gánh hàng chục luồng đọc/ghi video thô và render video thành phẩm liên tục của FFmpeg (hàng chục GB/giờ).
   - Cơ sở dữ liệu `state.db` chứa bảng `videos` với **46.444 dòng**, bảng `perceptual_hashes` 11.545 dòng.
2. **Thiếu Index thứ cấp (Missing Indexes)**:
   - Bảng `videos` ban đầu chỉ có duy nhất 1 Primary Key trên cột `video_id`.
   - Các câu lệnh kiểm tra số lượng video của folder:
     `SELECT COUNT(*) FROM videos WHERE folder=? AND status='downloaded'`
     bắt buộc SQLite phải quét toàn bộ bảng (Full Table Scan) 46.444 dòng từ đĩa cơ.
   - Đo thực tế trên ổ `D:`: Một câu query đơn giản mất tới **156.07 giây (hơn 2.5 phút)**!
   - Khi 20 worker download cùng chạy và gọi `BEGIN IMMEDIATE`, lock của SQLite bị giữ quá lâu, dẫn đến toàn bộ worker rơi vào trạng thái chờ I/O vô tận.
3. **So sánh tốc độ khi đưa lên SSD (Drive `C:`)**:
   - Chuyển `state.db` sang ổ SSD `C:`: Thời gian query từ 156 giây giảm xuống chỉ còn **0.013 giây (nhanh gấp 12.000 lần)**.

### Giải pháp bắt buộc
1. **Đánh Index bổ sung ngay lập tức cho `state.db`**:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_videos_folder_status ON videos(folder, status);
   CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
   CREATE INDEX IF NOT EXISTS idx_videos_channel_status ON videos(source_channel, status);
   CREATE INDEX IF NOT EXISTS idx_folders_status ON folders(status);
   ```
2. **Tách I/O database khỏi ổ render nặng**:
   - Nếu ổ `D:` đang gánh batch render nặng, nên đặt file `state.db` trên ổ SSD `C:` (ví dụ `C:/Users/Kibe/AppData/Local/Temp/fast_state.db` hoặc thư mục runtime trên SSD) và dùng flag `--state-db` trỏ tới file trên SSD.

---

## 2. Cơ Chế Xoay Proxy Tức Thì Khi Gặp Lỗi (Fail-Over Proxy)
### Vấn đề cũ
Trước đây, khi một cổng proxy trong pool (như cổng Mobi `5130` hoặc cổng bị từ chối kết nối `[WinError 10061] No connection could be made`) gặp lỗi, `yt-dlp` chỉ retry trên chính cổng proxy đó theo tham số `retries`. Hậu quả: worker download bị kẹt timeout hàng chục giây đến vài phút trên cổng chết.

### Cơ chế Fail-Over chuẩn (User correction 12/09/2026: "Lỗi 1m proxy đó thì đổi proxy khác mà download")
1. **Bọc vòng lặp đổi Proxy trong `download_candidate()`**:
   ```python
   max_dl_attempts = 3
   for dl_attempt in range(max_dl_attempts):
       options = yt_options(args, flat=False, download=True)
       proxy = _worker_proxy(args) or next_proxy(args)
       if proxy:
           options["proxy"] = proxy
       options["outtmpl"] = str(job / "%(title).160s [%(id)s].%(ext)s")
       try:
           with yt_dlp.YoutubeDL(options) as ydl:
               ydl.download([candidate.url])
       except Exception as _dl_err:
           if dl_attempt == max_dl_attempts - 1:
               raise
       media = sorted([p for p in job.rglob("*") if p.is_file() and p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov", ".m4v"}])
       if media:
           break
   ```
2. **Bọc đổi Proxy trong `discover_source()`**:
   - Khi quét danh sách video listing của kênh (Shorts / Videos), bọc vòng lặp 3 lần thử: mỗi lần thử thất bại do proxy hoặc mạng, tự động gọi `next_proxy(args)` bốc ngay proxy mới từ pool để crawl lại mà không dừng kênh.

---

## 3. Xử Lý Nghẽn `insufficient_pool` Trên Các Ngách Hẹp
### Nguyên nhân
Khi mở rộng tải thêm 40 folder cho Slot 7 & Slot 8 (Máy 61..80, dải folder 481..640):
- Một số ngách hẹp (`nhac`, `laptrinh`, `suckhoe`, `vantay`, `langque`, `sukien`) trong `sources.qualified30.json` chỉ có 4 – 8 kênh.
- Do các máy 1..60 đã claim hết các kênh này theo luật `--max-folders-per-channel 1`, các folder 487, 503, 527, 543, 559, 568 không còn kênh nào hợp lệ trong `eligible_sources` $\rightarrow$ bị chuyển sang `insufficient_pool`.

### Cách xử lý chuẩn
1. **Nâng `--max-folders-per-channel 2`**:
   - Với các kênh qualified có nhiều video (60 – 90 Shorts), cho phép gán tối đa 2 folder/kênh (mỗi folder bốc các video khác nhau nhờ `dedup` qua bảng `videos` và perceptual hashes).
2. **Bổ sung nguồn (Discovery tiếp)**:
   - Dùng `source_pool_builder.py` quét bổ sung thêm các kênh mới cho các niche ngách đang thiếu nguồn.

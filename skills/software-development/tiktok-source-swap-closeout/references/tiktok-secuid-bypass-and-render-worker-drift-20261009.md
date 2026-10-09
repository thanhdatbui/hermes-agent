# TikTok SecUID Playlist Crawl Bypass and Background Render Worker Collision (2026-10-09)

## 1. Context & Incident
Tài khoản TikTok `@yuethutiubk` (Máy 62, Tik 8) có hiện tượng lệch nội dung nghiêm trọng:
- 5 video ban đầu đăng tệp bạn nữ sinh viên / agency / daily vlog (view lên tới 765, 57 tim, 11 follower).
- 3 video mới nhất đột ngột biến thành clip Camera giao thông (dashcam tai nạn, view tụt thảm hại xuống đúng 48 view).
- Avatar tài khoản bị watchdog tự động đổi thành ảnh tròn vàng dính chữ "hôi" (do cắt lẹm từ banner chữ "thôi" trong clip tai nạn của folder 496).

## 2. Truy Vết Nguyên Nhân Gốc (Root Cause)
1. **Lệch Nguồn Folder 496:** Thư mục `D:\video goc\496` bị tải đè kênh `@Cameragiaothong` vào ngày 11/09/2026.
2. **Lỗi Trôi Cursor Trong Excel:** Trong `Tik8.xlsx`, hàng Máy 62 gán `Folder Video = 496`, nhưng cột `Video Đã Đăng` bị reset về 0 thay vì ghi nhận 5 clip đã có trên kênh. Khi bot chạy upload, nó bốc `1.mp4, 2.mp4, 3.mp4` của folder 496 (tai nạn) để đăng lên kênh.
3. **Lỗi Avatar Watchdog Cắt Tự Động:** Watchdog ca tối thấy folder 496 nên gọi `_make_avatar.py` cắt frame 1 từ `1.mp4` (banner tai nạn vàng chữ "thôi") $\to$ thành chữ "hôi" màu vàng.
4. **Xung Đột Render Worker Chạy Ngầm (`run_kibe_render_worker.py`):**
   - Trong `Tik8.xlsx`, cột `video gốc` bị gán là `622` (ToyStation / Top 1 Khám Phá), còn `Folder Video` là `496`.
   - Tiến trình nền `run_kibe_render_worker.py` (PID 31464) liên tục quét thấy `out_cnt < 45` và âm thầm gọi `random_batch_render.py` nạp `D:\video goc\622` render vào `D:\TIKTOK-videonuoinick\496`, khóa cứng file `3.mp4` (`WinError 32: process cannot access the file`).

## 3. Giải Pháp & Kỹ Thuật Đột Phá

### 3.1. Kỹ Thuật Cào Kênh TikTok Qua `sec_uid` (Bypass Lỗi Secondary User ID)
- Khi gọi `yt-dlp https://www.tiktok.com/@username`, yt-dlp thường crash với lỗi:
  `ERROR: [tiktok:user] username: Unable to extract secondary user ID`.
- **Quy trình chuẩn vượt rào:**
  1. Gửi request đơn giản đến `https://www.tiktok.com/@username` với standard browser User-Agent (`Mozilla/5.0...`).
  2. Dùng Regex trích xuất chuỗi `secUid` từ mã HTML:
     `sec_uid = re.search(r'\"secUid\":\"([^\"]+)\"', html).group(1)`
     (chuỗi dạng `MS4wLjABAAAA...`).
  3. Cung cấp URL playlist dạng `https://www.tiktok.com/@<sec_uid>` cho yt-dlp:
     `yt-dlp --flat-playlist --print "%(id)s | %(duration)s" "https://www.tiktok.com/@<sec_uid>"`
  4. yt-dlp nhận diện trực tiếp playlist kênh, quét được toàn bộ 150+ video và tải với tốc độ tối đa (10-15 MB/s), 100% không bị bot-check hay HTTP 429.

### 3.2. Đồng Bộ Lại Worker Render Ngầm
- Khi hoán đổi folder, nếu `run_kibe_render_worker.py` đang chạy, BẮT BUỘC cập nhật đồng thời trong `Tik<N>.xlsx`:
  - `video gốc` = `Folder Video` (ví dụ cùng là `496`).
  - `Keyword Video` = Ngách mới (`Đời sống`).
  - `Video Đã Đăng` = Số video thực tế đã có trên TikTok (ví dụ `8`).
- Khi `Tik<N>.xlsx` được cập nhật, worker nền sẽ nhận diện `src_id == out_id` và tự động render đúng nguồn mới mà không ghi đè rác từ folder cũ.

### 3.3. Rào Chắn Device Lock An Toàn (Anti-Collision Với 2FA)
- Kiểm tra lock file tại `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`.
- Khi máy đang chạy tác vụ quan trọng (như bật 2FA `tiktok-add-bao-mat-f2a`):
  - TUYỆT ĐỐI CẤM tranh chấp lock hoặc kill tiến trình.
  - Cập nhật bảng `avatar_replace_queue` trong `tiktok_tracker.db` về `status = 'PENDING'` (`updated_at = datetime('now','localtime')`).
  - Trả về telemetry `SKIPPED_LOCKED`. Watchdog ca tối sẽ tự động bốc máy upload avatar mới ngay khi tiến trình 2FA hoàn tất và nhả lock.

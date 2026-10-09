# TikTok sec_uid Playlist Extraction & Interleaved Bad Video Purge (2026-10-09)

## Context & Incident
Tài khoản `@yuethutiubk` (Máy 62, Tik 8) có 5 clip đầu là video vlog đời sống bạn nữ sinh viên/agency kéo view tự nhiên rất tốt (clip concert 765 views), nhưng 3 clip gần nhất bị đăng nhầm sang camera tai nạn giao thông (kẹt đáy 48 views). File avatar cũng bị cắt trúng chữ "hôi" từ banner màu vàng của video tai nạn giao thông.

## 1. Truy Vết Lịch Sử DB & Nguyên Nhân Kênh Bị Đè
- **Hệ thống lưu vết tải kênh:**
  1. `C:\CodexRuntime\tiktok-video\state.db` (34MB): Bảng `folders` và `videos` lưu metadata của hơn 57.600 clip tải về.
  2. `D:\OneDrive\SharedData\tiktok-video\global-ledger\*.jsonl`: Lưu lịch sử `source_claimed` và `downloaded` theo số folder.
- **Tại sao kênh cũ không còn trong DB:**
  - Tài khoản reg ngày 25/08/2026, đợt cào đầu tiên là batch thủ công trước khi chuẩn hóa `state.db` tập trung.
  - Ngày 11/09/2026, đợt chuẩn hóa 640 folder đã gán folder 496 vào `@Cameragiaothong` và ghi đè `state.db`.
  - File workbook `Tik8.xlsx` khi tạo bị để `Video Đã Đăng = 0`, khiến bot tự động upload tiếp `1.mp4, 2.mp4, 3.mp4` của folder 496 (tai nạn giao thông) lên tài khoản.

## 2. Kỹ Thuật Bóc Playlist TikTok Bằng `sec_uid` (Bypass Bot-check & Secondary User ID Error)
- **Vấn đề với YouTube Shorts:**
  - yt-dlp tải YouTube Shorts liên tục rất dễ dính `HTTP Error 429: Too Many Requests` và bot-check *"Sign in to confirm you're not a bot"*, làm treo pipeline nếu proxy MikroTik rớt.
- **Vấn đề với TikTok username thông thường:**
  - yt-dlp cào `https://www.tiktok.com/@<username>` thường bị lỗi:
    `ERROR: [tiktok:user] <username>: Unable to extract secondary user ID.`
- **Giải pháp bóc `sec_uid` siêu tốc (<0.5s):**
  1. Gửi request GET đơn giản đến `https://www.tiktok.com/@<username>` với User-Agent chuẩn.
  2. Trích xuất regex: `re.search(r'"secUid":"([^"]+)"', html).group(1)`.
  3. Xây dựng URL playlist: `https://www.tiktok.com/@<sec_uid>` (chuỗi bắt đầu bằng `MS4wLjABAAAA...`).
  4. yt-dlp nhận diện trực tiếp playlist của user mà không cần tra cứu phụ:
     `yt-dlp --flat-playlist --print "%(id)s | %(duration)s" "https://www.tiktok.com/@<sec_uid>"`
  5. Tải video TikTok trực tiếp đạt tốc độ 12 - 18 MB/s, giải JS challenge nội bộ, không dính rate limit.

## 3. Quy Trình Purge & Bảo Tồn Cursor Khi Đổi Nguồn Cho Kênh Bị Đăng Nhầm
1. **Xóa sạch video rác cũ:** Xóa toàn bộ file video trong cả `D:\video goc\<Folder>` và `D:\TIKTOK-videonuoinick\<Folder>`.
2. **Bảo tồn Cursor `start_seq`:**
   - Trên tài khoản TikTok thật đã có $N$ video (ví dụ 5 clip cũ + 3 clip đăng nhầm = 8 video).
   - Thiết lập `start_seq = N + 1 = 9`.
   - Cập nhật workbook `Tik<Slot>.xlsx`: `Video Đã Đăng = 8`.
   - Khi chạy `random_batch_render.py` với `--start-seq 9`, các video render thành phẩm sẽ được đánh số từ `9.mp4`, `10.mp4`, ... `53.mp4`.
   - Ca upload tiếp theo, bot sẽ bốc chính xác `9.mp4` để đăng, không làm mất bất kỳ clip mới nào và không bị trùng lặp index.
3. **Xử lý các clip lỗi trên kênh:**
   - Hướng dẫn Operator chuyển các clip đăng nhầm view thấp sang chế độ *"Chỉ mình tôi"* (Private) để lưới video Profile thuần 100% tệp nội dung mới.
4. **Đồng bộ Avatar & Reset Queue:**
   - Đặt file avatar chuẩn niche vào cả 2 đầu kho (`video goc` và `TIKTOK-videonuoinick`).
   - Cập nhật SQLite `avatar_replace_queue` về `status = 'PENDING'` để watchdog hoặc runner tự động cập nhật lên thiết bị.

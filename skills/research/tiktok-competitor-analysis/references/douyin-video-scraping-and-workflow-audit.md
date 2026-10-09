# Douyin Video Scraping & Workflow Audit Protocol

## 1. Cào Video Visual Gốc từ Douyin (TikTok Trung Quốc)

### Tại sao nên dùng nguồn Douyin:
- 100% video visual/gái xinh bắt trend tại VN đều bắt nguồn từ Douyin.
- Video 1080p nét căng, không dính logo watermark của TikTok VN.
- Thuật toán TikTok VN nhận diện là video hoàn toàn mới khi qua bộ render FFmpeg random.

### Cách tải trực tiếp qua script `download_douyin_visual.py`:
- Thư viện `yt-dlp` có sẵn extractor cho Douyin.
- **Xử lý Shortlink `v.douyin.com`**:
  - Dùng `requests.get(url, allow_redirects=True)` để lấy URL canonical `https://www.douyin.com/video/<id>`.
  - Nạp link canonical vào `yt-dlp` với cấu hình format `bestvideo+bestaudio/best`.
- **Lệnh thực thi**:
  ```bash
  python D:/Taadaa/Tiktok-video/scripts/download_douyin_visual.py --urls "https://v.douyin.com/xyz/" --output-dir "D:/video goc/7"
  # Hoặc đọc file danh sách:
  python D:/Taadaa/Tiktok-video/scripts/download_douyin_visual.py --file links.txt --output-dir "D:/video goc/7"
  ```

### Cách tải nâng cao & chuyên dụng qua CLI `f2` (v0.0.1.7+):
Công cụ chuyên dụng `f2 dy` (Douyin CLI downloader) nằm sẵn trong venv Hermes (`.../venv/Scripts/f2`).
- **Ưu điểm**: Hỗ trợ bóc video không watermark siêu tốc, tải hàng loạt theo profile/post/mix/collection, tự parse shortlink `v.douyin.com`, nhận proxy qua `-P`.
- **Cú pháp tải video đơn lẻ (single post)**:
  ```bash
  f2 dy -u "<DOUYIN_URL_HOAC_SHORTLINK>" -M one -p "<OUTPUT_DIR>"
  ```
- **Tải kèm proxy (nếu bị rate-limit hoặc chặn vùng IP)**:
  *Lưu ý quan trọng về cú pháp `f2`*: Flag `-P` / `--proxies` của `f2` bắt buộc nhận **2 đối số** (tương ứng cho HTTP và HTTPS). Nếu chỉ truyền 1 tham số sẽ văng lỗi `Error: Option '-P' requires 2 arguments.`.
  ```bash
  # Tận dụng pool proxy farm (truyền đủ 2 tham số http và https):
  f2 dy -u "<DOUYIN_URL>" -M one -p "<OUTPUT_DIR>" -P "http://user:pass@ip:port" "http://user:pass@ip:port"
  ```
- **Xử lý WAF / Anti-bot Douyin (`HTTP 403 Forbidden` / `Fresh cookies are needed`)**:
  Douyin áp dụng WAF với thuật toán anti-crawler `a_bogus` và JS challenge (`_$jsvmprt`, `__ac_signature`). Cả `f2 dy` và `yt-dlp` khi gọi endpoint `/aweme/v1/web/aweme/detail/` không có session cookie sẽ bị trả về rỗng (HTTP 200 empty) hoặc dính `HTTP 403 Forbidden` / `APIRetryExhaustedError`.
  - **Cách khắc phục**:
    1. Bắt buộc truyền cookie còn hạn (có `passport_csrf_token`, `__ac_nonce`, `__ac_signature` hoặc `sessionid`):
       ```bash
       f2 dy -u "<DOUYIN_URL>" -M one -p "<OUTPUT_DIR>" -k "<COOKIE_STRING>"
       # Hoặc với yt-dlp:
       yt-dlp --cookies douyin_cookies.txt -o "<OUTPUT_DIR>/%(id)s.%(ext)s" "<DOUYIN_URL>"
       ```
    2. **Lưu ý về `--cookies-from-browser` trên Windows**: Nếu trình duyệt Chrome/Edge đang mở, file SQLite cookie bị hệ điều hành lock và yt-dlp sẽ báo lỗi `ERROR: no such table: meta` hoặc `Could not copy Chrome cookie database`. Cần đóng hoàn toàn trình duyệt hoặc xuất cookie ra file text trước khi gọi.
- **Kiểm tra thông số kỹ thuật (ffprobe)**:
  ```bash
  ffprobe -v error -select_streams v:0 -show_entries stream=width,height,codec_name,duration,bit_rate -of default=noprint_wrappers=1 "<file_video.mp4>"
  ```
- **Trích xuất ảnh frame bằng chứng (ffmpeg)**:
  ```bash
  ffmpeg -y -ss 00:00:02 -i "<file_video.mp4>" -vframes 1 "<output_frame.jpg>"
  ```

---

## 2. Quy Trình Cào Tự Động Douyin Thuần Nhạc (Anti-Speech & Anti-Anime)

### Quy tắc bất biến từ phản hồi User:
- **CẤM BẮT USER GỬI LINK DOUYIN/TIẾNG TRUNG**: User không biết tiếng Trung, giao phó toàn bộ việc tìm kiếm, chọn lọc và tải cho Agent. Agent phải tự động 100% từ khâu tìm creator đến bóc tách video.
- **Yêu cầu nội dung**: 100% gái xinh người thật, góc quay dọc visual, thuần nhạc nền (dance, biến hình, OOTD). Cấm tiệt anime, hoạt hình, 3D, game, review ẩm thực/công nghệ và clip có tiếng nói tiếng Trung lảm nhảm.

### Pitfall chí mạng: Lỗi treo 30s của `f2` do Bark Notification (`enable_bark: true`):
- Trong file cấu hình mặc định của `f2` (`venv/Lib/site-packages/f2/conf/conf.yaml`), tham số `enable_bark: true` được bật sẵn. Khi tải video hoặc gặp lỗi, `f2` tự động gửi request đến `https://api.day.app/`. Do không có Bark key hợp lệ, request này bị timeout 30s hoặc văng `405 Method Not Allowed`, làm tê liệt toàn bộ script crawler đa luồng.
- **Fix triệt để**: Bắt buộc sửa `enable_bark: false` trong `f2/conf/conf.yaml`.

### Bẫy Douyin Web PC vs Giải pháp Săn Creator qua HTML Sitemap:
- **Bẫy Web PC**: Giao diện web Douyin (`/jingxuan`) ưu tiên video dài 30-40 phút (phim tài liệu, anime, review). Tính năng tìm kiếm (`/search/`) bị chặn cứng bởi login modal (`douyin_login_new_class`) và slider captcha (`rc-verifycenter`).
- **Giải pháp bóc tách O(1) qua Sitemap**: Douyin công khai toàn bộ creator và hashtag qua các trang sitemap SSR:
  - `https://www.douyin.com/htmlmap/hotauthor_0_<page>` và `douauthor_0_<page>` (chứa hơn 200.000 creator).
  - Quét chuỗi `defaultEntityLinkList` trong HTML bằng regex:
    ```python
    import requests, re
    r = requests.get('https://www.douyin.com/htmlmap/hotauthor_0_1', headers={'User-Agent': 'Mozilla/5.0'}).text
    r_clean = r.replace(chr(92) + chr(34), chr(34))
    creators = re.findall(r'\"entityName\":\"(.*?)\",\"linkUrl\":\"(https://www.douyin.com/user/MS4wLjABAAAA[a-zA-Z0-9_\-]+)\"', r_clean)
    ```
  - Lọc theo keyword bạn nữ nhảy/visual: `['舞蹈生', '跳舞', '甜妹', '学姐', '穿搭', 'yuki', 'dance', '纯欲']`, loại trừ `['机构', '培训', '少儿', '招生', '广场舞', '剧', '游戏']`.
  - Nạp link profile vào `f2 dy -u <url> -M post -o <count> -k <cookie_str> -p <dir>` để kéo toàn bộ video ngắn của riêng bạn nữ đó.

### Bộ Lọc Kép Bắt Buộc (AI Vision + AI Whisper):
1. **AI Vision ViT ONNX (`scripts.ai_channel_filter.AIFemaleFilter`)**:
   - Quét 3 frame (2s, 5s, 8s). Nâng ngưỡng `score >= 0.75` (75% nữ người thật) để loại bỏ hoàn toàn nhân vật hoạt hình 2D/3D hoặc nam giới.
2. **AI Audio Whisper (`faster_whisper` tiny int8 CPU)**:
   - Trích xuất 30s âm thanh đầu sang WAV.
   - Hễ phát hiện `info.language == 'zh'` (tiếng Trung nói chuyện) -> REJECT và xóa file ngay lập tức.
   - CHỈ giữ lại video `no_speech` (thuần nhạc remix/dance) hoặc câu chào cực ngắn (<5 từ) chìm trong nhạc.

---

## 3. Rà Soát Workflow Tự Động Hóa Bên Ngoài (GemLogin / Automa)

Khi nhận file workflow `.gemlogin` hoặc `.json` từ bên ngoài để kiểm tra logic:
1. **Kiểm tra tính liên tục của đồ thị (Graph Connectivity)**:
   - Nhiều workflow bị "đứt dây": nhánh từ `trigger` chỉ chạy một vài node rồi cụt, trong khi 70% các node chính nằm ở một cụm cô lập không bao giờ được kích hoạt.
   - Luôn dựng đồ thị incoming/outgoing edges để tìm các node mồ côi.
2. **Kiểm tra Kill-Switch (Bom hẹn giờ)**:
   - Các script chia sẻ trên mạng hay bị cài mã chặn ngày hết hạn ngầm trong block JavaScript:
     ```javascript
     const expirationDate = new Date("2026-12-28");
     if (new Date() > expirationDate) throw new Error("Hết hạn!");
     ```
3. **Phát hiện Hardcoded User Paths**:
   - Tìm kiếm các đường dẫn tĩnh như `C:\Users\<tên_người_lạ>\Downloads\...` trong params và lệnh CMD/PowerShell. Chuyển sang biến môi trường `%USERPROFILE%` hoặc `Path.home()`.
4. **Tránh cào qua các trang trung gian (như Snaptik web)**:
   - Các web tải trung gian luôn dính Cloudflare CAPTCHA / Turnstile sau 2-3 lượt tải. Luôn ưu tiên dùng `yt-dlp` hoặc API trực tiếp thay vì lái browser vào web trung gian.

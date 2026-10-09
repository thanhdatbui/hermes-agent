# Video Sourcing: Hai Tầng Phân Bổ (Độc Quyền vs Bể Gộp Đa Dạng) & Chuẩn Hóa Niche Gái Xinh

> 📌 **User Directive (2026-09-23 / 2026-09-24)**: 
> - Mặc định kênh đủ >= 40 video: Nạp trọn vẹn 1 kênh = 1 folder độc quyền (Exclusive).
> - Kênh thiếu (< 40 video): Gom vào bể gộp, nạp vào folder tổng hợp với thuật toán **phân bổ đa dạng từ TẤT CẢ các kênh thiếu**, random số lượng giữa các kênh.
> - **Cơ chế Cắt Lát 45 Video & Bể Gộp Thặng Dư (Leftover Pool)**: Kênh độc quyền lấy tối đa 45 video đầu (`vids[:45]`), toàn bộ video từ clip 46 trở đi được gom đẩy sang Bể Gộp đa kênh để tái sử dụng, không bỏ phí.
> - **Chống trùng nguồn tuyệt đối (`gaixinh_claims.py`)**: Ghi nhận quyền sở hữu kênh tập trung (`gaixinh_channel_claims.json`) và folder-level marker (`channel_info.json`). Cấm 2 folder nhận trùng 1 kênh.
> - **CẤM TUYỆT ĐỐI bắt User đi xem / check link thủ công** ("tao bảo mày đi cào link h mày bắt t đi nhìn"). Agent phải tự động cào và verify bằng script AI Vision tự động 100%.
> - **Cấu hình tải & render hàng loạt**: Render dùng **2 workers** (`--parallel 2`) trên server 56 cores để rút ngắn thời gian còn ~3.5 phút/folder; Tải dùng **20 workers đa luồng qua proxy pool**; Cào Douyin dùng **10 workers** kết hợp AI Whisper lọc bỏ tiếng Trung.
- **Kỷ luật Độc Quyền Trước (Exclusive First) - Thừa mới đẩy Bể Gộp**: Luôn ưu tiên nạp 1 bạn nữ duy nhất vào 1 folder độc quyền (đủ 40–45 clip). Chỉ khi kênh đó thừa video từ clip 46 trở đi mới dồn vào Bể Gộp đa kênh (`curated_pool`) để dùng dần, cấm trộn tạp nham từ đầu.
- **Kỷ luật lưu trữ ổ đĩa & Naming**: CẤM tải/lưu video số lượng lớn vào ổ C (chỉ dùng ổ D:\video goc\...). File cấu hình f2 app.yaml đặt `naming: '{create}_{aweme_id}'` để tránh lỗi đường dẫn quá dài hoặc ký tự lạ tiếng Trung gây hỏng filesystem Windows. Cấm rglob quét đĩa sâu trên Windows.

---

## 1. Chiến Lược Phân Bổ 2 Tầng (Exclusive vs Curated Hub) & Giới Hạn Min 40 Max 45

### Quy Tắc Min 40 (45 là MIN chứ KHÔNG PHẢI MAX CỨNG) & CẤM TẠO FOLDER PHỤ (User Directive 2026-10-07)
- **45 là MIN, KHÔNG PHẢI MAX**: Chỉ tiêu mỗi folder tối thiểu 40–45 clip để đạt chuẩn nuôi (`--min-videos 40`). Nhưng **45 clip là mốc tối thiểu, KHÔNG phải trần cứng (cap)**.
- **CẤM TẠO FOLDER PHỤ GỐI ĐẦU LẮT NHẮT**: Khi một kênh tải về có 70–100 video (ví dụ 70 clip), **ĐẨY THẲNG TOÀN BỘ VÀO FOLDER ĐÓ** (đánh số nối tiếp `1.mp4..70.mp4` trong `D:\video goc\<folder>`). **TUYỆT ĐỐI CẤM TỰ Ý TẠO THÊM FOLDER TẠM/PHỤ** (như `<folder>_goi_dau_dot2`) làm rối rắm filesystem và phát sinh bước gộp thừa thãi!
- **Render nối tiếp không mất video cũ**: Sử dụng cờ `--resume-verify-existing` của `random_batch_render.py` để giữ nguyên các video `1.mp4..45.mp4` đã render hợp lệ trước đó và tự động render nối tiếp từ `46.mp4..70.mp4`. Kênh có sẵn 70 video nuôi một lèo 7–8 tháng không lo cạn đạn.
- **Xử lý phần dư dôi lớn (> 100+ clip)**: Chỉ khi kênh tải về số lượng quá lớn (200–300+ clip), sau khi nạp đủ 45–70 clip cho folder chính, số lượng dôi dư còn lại (200+ clip) mới được gom đẩy sang `curated_pool` (đặt tên tiền tố `<uploader>_<id>.mp4`) để chia sẻ nuôi các kênh tổng hợp đa kênh trong farm.

### Tầng 1: Độc Quyền (Exclusive - Ưu tiên số 1)
- Áp dụng khi kênh nguồn có sẵn **>= 40 video hợp lệ** (chuẩn thời lượng 10s - 45s).
- **Quy tắc**: Nạp trọn vẹn duy nhất 1 kênh vào 1 folder.
- **Mục đích**: Định vị tài khoản idol/cá nhân, profile 100% cùng 1 khuôn mặt (giống công thức 2 kênh triệu view `@trn.t.t85` và `@hong.thy.qunhhh`).

### Tầng 2: Bể Gộp Tổng Hợp (Curated Hub - Khi gặp kênh thiếu)
- Chỉ kích hoạt khi quét trúng các kênh chất lượng nhưng **số lượng video < 40**.
- **Thuật toán Đa Dạng Hóa Tối Đa (Diversity Distribution Invariant)**:
  - Nếu trong bể có K kênh thiếu (ví dụ: 8–9 kênh): **MỖI FOLDER BỂ GỘP BẮT BUỘC PHẢI CHỨA VIDEO TỪ TẤT CẢ K KÊNH ĐÓ**.
  - **Random số lượng biến thiên**: Mỗi bạn nữ đóng góp một số lượng video ngẫu nhiên (ví dụ bạn A: 4 clip, bạn B: 5 clip, bạn C: 3 clip... tổng cộng >= 40 clip).
  - **Xáo trộn (Shuffle)**: Toàn bộ video trong folder được shuffle đều tay để khi lướt feed/đăng video mỗi ngày là một bạn nữ khác nhau xoay vòng.
  - **CẤM TUYỆT ĐỐI**: Gom cục bộ 2-3 kênh vào 1 folder khiến các folder bị nghèo nàn và trùng lặp nhân vật.

---

## 2. Kỷ Luật Xác Thực Nguồn Tự Động Bằng AI (Zero User Manual Check)

### Cạm bẫy đoán mò ID (String Guessing Trap)
- Tuyệt đối KHÔNG tự ý đoán ID tài khoản TikTok bằng chuỗi văn bản (ví dụ thêm dấu chấm vào tên người nổi tiếng):
  - `@tra.dang.97` (có dấu chấm) -> Tài khoản clone trẻ con chơi Toca Boca slime (`toca..boca..101`), không có video gái xinh!
  - `@douyinvn` -> Kênh tạp nham reup clip trai đẹp (`#ngamtraidep`).
- **Hậu quả**: Nạp video rác vào folder, khiến user bức xúc.
- **Quy tắc**: CẤM bắt user ngồi check link hay xác nhận mắt ("tao bảo mày đi cào link h mày bắt t đi nhìn"). Mọi bước kiểm duyệt phải chạy tự động ngầm.

### Tự động hóa 100% qua AI 2 Tầng (`ai_channel_filter.py`)
1. **Lớp 1: NLP Blacklist Filter (Lọc Kênh Trước Khi Tải)**:
   - Tự động chuẩn hóa văn bản bỏ dấu (`strip_accents`).
   - Kiểm tra Blacklist keywords: `['toca', 'boca', 'game', 'gaming', 'roblox', 'freefire', 'lienquan', 'traidep', 'ngamtraidep', 'hoathinh', 'slime', 'review']`. Nếu chứa bất kỳ từ nào -> REJECT ngay từ đầu.
   - Kiểm tra Positive keywords: `['gai', 'xinh', 'douyin', 'dance', 'nhay', 'visual', 'beauty', 'cute', 'model', 'ootd']`.
2. **Lớp 2: AI Vision ViT ONNX (Kiểm Duyệt Từng Khung Hình Sau Khi Tải)**:
   - Tải model ViT Image Classification lượng tử hóa (`onnx-community/gender-classification-ONNX`) lưu tại `D:\Taadaa\Tiktok-video\models\onnx\model_quantized.onnx`.
   - **Normalization chuẩn ViT (BẮT BUỘC)**:
     ```python
     # ViT normalization chuẩn theo preprocessor_config: mean=0.5, std=0.5
     arr = (arr - 0.5) / 0.5
     ```
     *(CẤM dùng ImageNet mean `[0.485, 0.456, 0.406]` vì sẽ làm sai lệch xác suất, nhận diện bạn nữ thành nam giới hoặc ngược lại).*
   - Tự động cắt 2-3 frame ở giây thứ 2 và giây thứ 5 bằng `ffmpeg`.
   - Chạy inference qua `onnxruntime` CPU (siêu nhanh ~0.05s/frame, 100% offline).
   - Nếu `female_prob >= 0.60` -> `[AI VISION PASS]`, giữ lại video.
   - Nếu là game, hoạt hình, nam giới, cảnh vật -> `[AI VISION REJECT]`, lập tức xóa file MP4 và tự động tải candidate khác bù vào.

---

## 3. Khắc Phục Lỗi Mất Thumbnail Preview HEVC trên Windows 10

### Hiện tượng
Trong Explorer tại `D:\video goc\<folder>`, toàn bộ video TikTok/Douyin tải về chỉ hiện icon hình nón cam của VLC thay vì ảnh thumbnail preview khuôn mặt.

### Nguyên nhân
TikTok/Douyin mã hóa video chất lượng cao 1080p bằng chuẩn **HEVC (H.265 / bytevc1)**. Windows 10 mặc định không có codec HEVC tích hợp sẵn nên Windows Explorer không thể giải mã tạo thumbnail.

### Cách xử lý triệt để
Cài đặt gói chính thức **Microsoft HEVC Video Extension** qua PowerShell:
```powershell
# 1. Tải và cài đặt Appx chính thức
Add-AppxPackage -Path "C:\Users\Kibe\Downloads\Microsoft.HEVCVideoExtension_x64.Appx"

# 2. Xóa thumbnail cache cũ và restart Explorer
Stop-Process -Name explorer -Force
Start-Sleep -Seconds 1
Remove-Item -Path "$env:LOCALAPPDATA\Microsoft\Windows\Explorer\thumbcache_*.db" -Force -ErrorAction SilentlyContinue
Start-Process explorer
```
Sau bước này, Windows Explorer sẽ hiển thị thumbnail thật cho 100% video MP4 HEVC.

---

## 4. Quy Trình Dọn Dẹp File Cũ (`--clean-old`)
Khi gán kênh mới hoặc chuyển đổi mục tiêu cho một folder (ví dụ từ niche cũ sang gái xinh):
- Bắt buộc xóa sạch 100% dữ liệu cũ trước khi tải mới:
  1. Thư mục raw: `D:\video goc\<folder>\*`
  2. Thư mục render tương ứng: `D:\TIKTOK-videonuoinick\<folder>\*`
- Script thực thi: `smart_gaixinh_distributor.py` với flag `--clean-old`.

---

## 5. Công Cụ & Script Thực Thi Chuẩn Hóa

### Script chính: `smart_gaixinh_distributor.py`
Nằm tại: `D:\Taadaa\Tiktok-video\scripts\smart_gaixinh_distributor.py`
- Tích hợp sẵn `AIFemaleFilter`, tự động kiểm duyệt NLP + ViT Vision.
- Hỗ trợ **Parallel Workers** (`--parallel`, mặc định 20 threads) tải song song qua `ThreadPoolExecutor`, tự động dừng worker ngay khi đạt đủ `min_videos`.
- Hỗ trợ **Proxy Pool** xoay tua round-robin (`--proxy-pool`, mặc định `D:/Taadaa/Tiktok-video/proxy_pool_67.txt`) cho các lệnh yt-dlp, tự động nhận diện và convert định dạng `host:port:user:pass`.
- ⚠️ **CẠM BẪY MẬT KHẨU PROXY CÓ KÝ TỰ ĐẶC BIỆT (`#`, `!`, `@`)**:
  - Mật khẩu proxy farm thường chứa `#` (ví dụ: `TaadaaMobi#2026!`).
  - Nếu format URL thô `http://{user}:{pwd}@{host}:{port}`, `yt-dlp` sẽ xem `#` là URL fragment dẫn đến lỗi crash: `ERROR: Failed to parse: http://mobi5:TaadaaMobi#2026!@test.taadaa.click:5105`.
  - **Bắt buộc URL-encode**:
    ```python
    user = urllib.parse.quote(parts[2], safe="")
    pwd = urllib.parse.quote(":".join(parts[3:]), safe="")
    valid.append(f"http://{user}:{pwd}@{host}:{port}")
    ```
    Biến `#` thành `%23` (`TaadaaMobi%232026%21`) để yt-dlp parse chuẩn và kết nối thành công.

- **Nạp kiểu Độc Quyền (1 người >= 40 clip)**:
  ```bash
  python D:/Taadaa/Tiktok-video/scripts/smart_gaixinh_distributor.py --folders 31 --mode exclusive --min-videos 40 --parallel 20 --proxy-pool D:/Taadaa/Tiktok-video/proxy_pool_67.txt --clean-old
  ```
- **Nạp kiểu Bể Gộp Đa Dạng (Tất cả kênh thiếu, random số lượng)**:
  ```bash
  python D:/Taadaa/Tiktok-video/scripts/smart_gaixinh_distributor.py --folders 63 --mode curated --min-videos 40 --parallel 20 --proxy-pool D:/Taadaa/Tiktok-video/proxy_pool_67.txt --clean-old
  ```
- **Tự động phân loại (Auto)**:
  ```bash
  python D:/Taadaa/Tiktok-video/scripts/smart_gaixinh_distributor.py --folders 127,135,159,175,191,239,247,263,287 --mode auto --min-videos 40 --clean-old --parallel 20 --proxy-pool D:/Taadaa/Tiktok-video/proxy_pool_67.txt
  ```

### File Manifest chuẩn hóa: `source_manifest_gaixinh.jsonl`
Nằm tại: `D:\Taadaa\Tiktok-video\data\source_manifest_gaixinh.jsonl`
Chứa danh sách 18 kênh gái xinh/visual đã qua xác thực thực tế (loại bỏ hoàn toàn kênh clone, kênh Toca Boca và kênh trai đẹp):
`gaixinh_moingay2026`, `gaixinh.nhaydep`, `gaixinhday.ne`, `gai_xinh_douyin18`, `gi.xinh.y46`, `hoaa.hanassii`, `vtkh2004`, `lebong95`, `thuy_tien_2000`, `ngoc.matcha`, `a3a3apzqayd`, `gai_xinh_mup`, `hnh999995`, `nbd0116`, `lachienthang4`, `ddlich2705`, `gaixinhdouyin86`, `gaixinhdouyin69`.

### Công cụ cào Douyin nội địa Trung Quốc
- `jiji262/douyin-downloader`: Tải batch theo profile Douyin (GUI Douzy + CLI).
- `Johnserf-Seed/f2` (`pip install f2`, đã cài đặt v0.0.1.7): CLI Python giải mã `a_bogus` / `msToken`, tải trực tiếp từ link profile Douyin:
  - Tải theo profile (kênh tác giả):
    ```bash
    f2 dy -u "https://www.douyin.com/user/MS4wLjABAAAA..." -M post -p "D:/video goc/31" -o 40 -k "<cookie_string>"
    ```
  - Tải 1 video lẻ (single video):
    ```bash
    f2 dy -u "https://www.douyin.com/video/<video_id>" -M one -p "D:/video goc/31" -k "<cookie_string>"
    ```
  - Kèm proxy qua tường lửa Trung Quốc / rate limit:
    ```bash
    f2 dy -u "<url>" -M one -p "<output_dir>" -P "http://user:pass@host:port" -k "<cookie_string>"
    ```
  - ⚠️ **LƯU Ý QUAN TRỌNG VỀ ANTI-BOT & COOKIE CỦA DOUYIN**:
    - Gọi trực tiếp `curl` hay HTTP request thô đến `douyin.com` sẽ bị server Tengine trả về `HTTP 404 Not Found`.
    - Chạy `f2` hoặc `yt-dlp` không có cookie sẽ bị WAF chặn với mã `HTTP 403 Forbidden` (`Fresh cookies needed`).
    - **Cách lấy cookie sống tự động qua Chrome CDP (port 9222)**:
      * Mở Chrome CDP điều hướng tới `https://www.douyin.com`.
      * Dùng lệnh WebSocket DevTools Protocol `Network.getCookies` để trích xuất danh sách cookie.
      * Ghép thành chuỗi `name1=val1; name2=val2...` và truyền thẳng vào tham số `-k "<cookie_string>"` của `f2 dy` (hoặc ghi ra file Netscape `cookies.txt` cho `yt-dlp`).
      * Kết quả đã verify thực tế: Kéo video MP4 Full HD 1080p (1920x1080), chuẩn H.264, âm thanh stereo, **sạch 100% không logo/watermark Douyin**.
- **Kỹ thuật đột phá: Bóc tách Profile Tác GiẢ Nữ (`f2 -M post`) qua API Detail**:
  * Cuộn feed thịnh hành chung (`/jingxuan`) của Douyin chứa đa dạng chủ đề (công nghệ, game, anime, ẩm thực). Dù AI ViT lọc chuẩn nhưng tỷ lệ video gái xinh trên feed chung chỉ đạt 5–10%, gây tốn thời gian loại bỏ.
  * **Giải pháp tối ưu**: Khi bắt gặp 1 video gái xinh trên feed, gọi API chi tiết của Douyin:
    `GET https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=<video_id>` (kèm cookie Chrome CDP)
    -> Trích xuất mã `author.sec_uid` (ví dụ `MS4wLjABAAAA...`).
  * Gọi lệnh kéo trọn gói cả kênh của bạn nữ đó:
    `f2 dy -u "https://www.douyin.com/user/<sec_uid>" -M post -o 40 -k "<cookie_string>" -p "D:/video goc/<folder>"`
    -> Đạt 100% video cùng 1 bạn nữ idol, Full HD không logo, AI ViT kiểm duyệt đạt 83%–98% điểm nữ.
- Script tự động hóa tích hợp: `D:\Taadaa\Tiktok-video\scripts\douyin_feed_ai_crawler.py` (hỗ trợ `--folder`, `--min-videos`, `--clean-old`, `--cdp-port 9222`).
- Script cào 10 workers + xuất ảnh grid bằng chứng: `scripts/run_douyin_crawler_10w.py` (tải song song qua `f2`, thẩm định 2 tầng AI ViT >= 0.75 + faster-whisper pure BGM, trích xuất frame giây thứ 2 và ghép ảnh grid contact-sheet tự động).

---

## 6. Cạm Bẫy TikTok Ảnh Ghép / Photo Slides (Audio-Only Stream Pitfall) Khi Render

### Triệu chứng lỗi
- `random_batch_render.py` hoặc `run_render_5_folders.py` kết thúc với `Exit code: 1`.
- File render xuất ra bị lỗi kích thước 0 byte (ví dụ: `19.mp4`, `20.mp4`, `21.mp4`, `23.mp4`, `28.mp4` tại Folder 63).
- Log FFmpeg ghi lỗi:
  ```text
  Stream specifier ':v' in filtergraph description [0:v]trim=... matches no streams.
  Error binding filtergraph inputs/outputs: Invalid argument
  ```

### Nguyên nhân gốc rễ
- Trên TikTok có nhiều bài đăng thực chất là **Album ảnh / Photo Slides (carousel ảnh kèm nhạc nền)**.
- Khi tải về, `yt-dlp` xuất ra file có đuôi `.mp4` nhưng bên trong thực tế **chỉ có 1 luồng âm thanh `mp3`, hoàn toàn không có luồng hình ảnh `video`** (`ffprobe -select_streams v:0` trả về rỗng).
- Khi đưa vào FFmpeg filtergraph với chỉ thị lọc hình `[0:v]`, FFmpeg không tìm thấy luồng video nào nên văng lỗi cú pháp và crash tiến trình render.

### Cơ chế phòng thủ & Xử lý (Prevention & Defense)
1. **Lọc ngay từ tầng tải (AI Vision Gate)**:
   - Module `AIFemaleFilter.verify_video_is_female()` tự động phát hiện lỗi này vì FFmpeg không thể cắt được frame từ file audio-only (`Could not extract frames from video, score=0.0%`).
   - Script tự động kích hoạt `[AI VISION REJECT]`, xóa ngay file MP4 rác khỏi đĩa và tiếp tục tải video có hình ảnh thật bù vào cho đến khi đủ chỉ tiêu.
2. **Kiểm tra Preflight trước khi Render (Stream Validator)**:
   - Trước khi đưa file nguồn vào danh sách render, bắt buộc kiểm tra xem có luồng video hay không:
     ```python
     import subprocess
     out = subprocess.run(
         ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', video_path],
         capture_output=True, text=True
     ).stdout.strip()
     if 'video' not in out:
         # File chi la audio/anh ghep -> Loai bo khoi danh sach render
         pass
     ```

---

## 7. Cơ Chế Chống Trùng Kênh Nguồn Xuyên Suốt Mọi Folder (Cross-Folder Channel Deduplication)

### Nguyên tắc cốt lõi (User Invariant 2026-09-24)
- **"Chống trùng nguồn là được"**: Để chống trùng triệt để giữa tất cả các folder trên toàn farm, giải pháp tối thượng và đơn giản nhất là **chống trùng kênh nguồn (source channel URL / uploader)**.
- Mỗi kênh nguồn một khi đã được chỉ định hoặc tải cho một folder thì **tuyệt đối không bao giờ được phép phân bổ cho bất kỳ folder nào khác** (kể cả khi chạy các đợt khác nhau, ngày khác nhau).

### Kiến trúc Lưu Vết Độc Quyền (Persistent Claims Architecture)
1. **Sổ cái đăng ký kênh tập trung (Central Claims Ledger)**:
   - Đường dẫn: `D:\Taadaa\Tiktok-video\data\gaixinh_channel_claims.json`.
   - Cấu trúc:
     ```json
     {
       "https://www.tiktok.com/@hoaa.hanassii": {"folder": "31", "uploader": "hoaa.hanassii", "claimed_at": "..."},
       "https://www.tiktok.com/@gi.xinh.y46": {"folder": "63", "uploader": "gi.xinh.y46", "claimed_at": "..."},
       "https://www.tiktok.com/@gaixinh_moingay2026": {"folder": "79", "uploader": "gaixinh_moingay2026", "claimed_at": "..."},
       "https://www.tiktok.com/@gaixinhday.ne": {"folder": "95", "uploader": "gaixinhday.ne", "claimed_at": "..."}
     }
     ```
2. **Vết đánh dấu tại từng folder nguồn (Folder-Level Marker)**:
   - Mỗi thư mục nguồn khi được tải nạp sẽ chứa file `D:\video goc\<folder_num>\channel_info.json`.
   - Giúp kiểm tra O(1) nguồn gốc của folder mà không cần quét lại dữ liệu toàn đĩa hay dò ngược DB.
3. **Module quản lý `scripts/gaixinh_claims.py`**:
   - `load_claims(claims_path, output_root)`: Đọc claims tập trung kết hợp đồng bộ các file `channel_info.json` hiện có.
   - `is_channel_claimed(claims, channel_url, current_folder)`: Kiểm tra xem URL kênh đã bị folder khác chiếm dụng chưa (chuẩn hóa key theo `@username`).
   - `claim_channel(...)`: Khóa kênh cho folder và ghi đĩa cả ở file claims lẫn `channel_info.json`.
   - `release_claim_for_folder(...)`: Tự động giải phóng kênh cũ khi chạy flag `--clean-old`.

### Quy trình điều phối trong `smart_gaixinh_distributor.py` và `download_gaixinh_pipeline.py`
- Trước khi quét candidate hay phân bổ:
  - Gọi `is_channel_claimed()`. Nếu đã thuộc folder khác -> `[SKIP CLAIMED] Bỏ qua kênh... Đã được gán cho folder X`.
  - Chỉ lọc ra danh sách các kênh chưa từng được claim để đưa vào `exclusive_channels` hoặc `curated_channels`.
  - Khi gán độc quyền cho một folder -> Gọi `claim_channel()` ghi nhận vĩnh viễn.
  - Trong `download_gaixinh_pipeline.py`: Khi chạy qua danh sách kênh trong manifest, bỏ qua kênh đã bị claim bởi folder khác (`is_channel_claimed()`), và khi tải thành công video cho folder mục tiêu, khóa claim kênh đó cho folder hiện tại.
  - Khi người dùng truyền flag `--clean-old`: Gọi `release_claim_for_folder(claims, folder_num, claims_path)` để dọn dẹp claim cũ trước khi nạp nguồn mới.

### Kiểm thử xác minh tự động (`tests/test_gaixinh_channel_dedup.py`)
Bộ test suite kiểm thử cơ chế chống trùng kênh bao gồm:
1. `test_claim_channel_and_persistence`: Xác minh claim mới được lưu atomic vào file claims JSON và `channel_info.json` trong folder.
2. `test_is_channel_claimed_cross_folder`: Đảm bảo kiểm tra trùng khớp bất kể khác biệt chữ hoa/thường hay URL vs `@username`.
3. `test_release_claim_on_clean_old`: Xác minh khi release folder cũ, kênh đó trở lại trạng thái khả dụng cho folder khác.
4. `test_load_claims_folder_discovery`: Kiểm tra khả năng tự phát hiện và sync claim từ các `channel_info.json` đã có sẵn trong các folder `D:/video goc/*`.

---

## 8. Bộ Lọc Ngôn Ngữ Âm Thanh Douyin & Chuẩn Thuần Nhạc Nền (Audio Language Gate Qua Faster-Whisper)

### Quy tắc chiến lược nuôi nick Farm SLL (User Invariant 2026-09-24)
- **Quy mô Phone Farm Nuôi Nick Số Lượng Lớn (SLL)**:
  - **TUYỆT ĐỐI KHÔNG CẦN DỊCH HAY LỒNG TIẾNG**: Dịch và lồng tiếng chỉ dành cho kênh bán hàng / affiliate quy mô nhỏ (1–5 nick trọng điểm). Với phone farm, mục tiêu là tài khoản sống dai, điểm Trust cao, view đề xuất đều đặn và chi phí vận hành nhẹ nhất.
  - **Chuẩn Content Duy Nhất Được Phép Nạp**: **THUẦN NHẠC NỀN (Nhảy Dance, Biến hình, Dạo phố khoe dáng, OOTD)**:
    1. Không có rào cản ngôn ngữ đối với khán giả Việt Nam.
    2. Tỷ lệ xem lặp lại (Loop Rate) cực cao khi người xem ngắm visual và nghe nhạc bắt tai -> TikTok tự động đẩy viral.
    3. Tự động hóa 100%, không tốn tài nguyên dịch thuật.

### Vấn đề thực tế video Douyin
Video cào từ Douyin nội địa thường có hai dạng:
1. **Dạng Thuần Nhạc (Dance, biến hình, khoe dáng, OOTD)**: Không có lời nói, chỉ có nhạc nền hoặc beat sôi động -> Phù hợp 100% để đăng lên TikTok Việt Nam.
2. **Dạng Vlog / Nói chuyện**: Tác giả nói tiếng Trung xuyên suốt (ví dụ: *"欢迎收看团播女主播... 一天Vlog"*). Nếu đăng lên nick TikTok Việt Nam sẽ làm tụt tỷ lệ giữ chân (Retention) và thuật toán dễ bóp reach.

### Giải pháp tự động lọc bằng AI Whisper (`verify_audio_no_speech`)
Sử dụng `faster_whisper` (model `tiny` int8, CPU chỉ tốn ~0.5s/video) tích hợp trực tiếp trong `scripts/ai_channel_filter.py`:
```python
def verify_audio_no_speech(self, video_path: str, max_check_seconds: int = 30) -> Tuple[bool, str, str]:
    # 1. Trích xuất audio 30s đầu sang WAV 16kHz mono
    # 2. Transcribe qua faster_whisper WhisperModel('tiny', device='cpu', compute_type='int8')
    # 3. Phân tích kết quả:
    #    - Không có text/speech: PASS (True, "no_speech", "PASS: Pure music/no speech detected")
    #    - info.language == 'zh': REJECT (False, "zh_speech", "REJECT: Chinese speech detected")
    #    - Ngôn ngữ khác nói liên tục (> 5 từ): REJECT (False, "speech_detected")
```
- **Xử lý nghiêm ngặt**:
  - Hễ phát hiện câu nói tiếng Trung (`zh_speech`) hoặc nói chuyện liên tục -> AI tự động xóa file MP4 ngay lập tức và tải ứng viên khác bù vào.
  - Chỉ chấp nhận video thuần nhạc nền / beat không lời nói lọt vào thư mục `D:\video goc\<folder>`.

---

## 9. Điều Phối Phân Bổ Tải: Render Tăng Tốc 2 Workers & Tải 20 Workers Qua Proxy

### Nguyên tắc tải CPU/GPU Host 56 Cores
- **Tốc độ lệch pha**: Download (20 workers) chỉ mất ~1-2 phút/folder, trong khi Render 1 worker mất ~10-12 phút/folder. Download nhanh gấp 5-8 lần Render.
- **Tăng tốc Render lên 2 Workers (`--parallel 2`)**:
  - Máy chủ có 56 logical cores (28 nhân thực) và 64GB RAM (trống > 35GB). Khi chạy 1 worker FFmpeg, CPU chỉ tải ~9-10%.
  - Nâng cấu hình render lên **2 workers song song (`--parallel 2`)**:
    * Thời gian render 1 folder 40 video **giảm một nửa từ ~12 phút xuống còn ~3.5 - 4 phút**.
    * CPU tải ổn định ở mức 70% – 85%, máy hoạt động mát mẻ, hoàn toàn triệt tiêu nguy cơ nghẽn hàng đợi (render queue starvation).
  - Script thực thi chuẩn Group 3: `run_render_group3.py` với `--parallel 2`.

---

## 10. AI ViT Ưu Tiên Avatar Mặt Nữ (Avatar Female Priority Trong Pipeline Common)

### Bối cảnh & Vấn đề
- Khi render hoặc chuẩn bị profile kênh, hàm `make_representative_avatar` trong `scripts/pipeline_common.py` trích xuất các cụm khuôn mặt từ video để tạo ảnh đại diện `avatar.jpg`.
- Trước đây, hệ thống chọn cụm có số lần xuất hiện nhiều nhất (`count`) hoặc độ nét cao nhất (`quality`).
- Nhược điểm: Nếu trong video có người đi đường là nam hoặc bạn diễn nam xuất hiện nhiều khung hình, avatar đại diện của kênh có thể bị chọn nhầm thành khuôn mặt nam.

### Cơ chế lựa chọn ưu tiên nữ
- Tích hợp `AIFemaleFilter` (ViT ONNX) trực tiếp vào `make_representative_avatar`:
  - Mỗi cụm khuôn mặt người (`kind == "person"`) được đưa qua `female_filter.classify_frame(cluster["crop"])`.
  - Đánh dấu `is_female` và `female_prob`.
  - Tách riêng danh sách các cụm nữ: `female_clusters = [c for c in clusters if c.get("is_female")]`.
  - Nếu có cụm nữ: Bắt buộc chọn avatar từ cụm nữ tốt nhất (`max(female_clusters, key=...)`).
  - Chỉ khi video hoàn toàn không tìm thấy cụm nữ nào mới fallback về cụm thông thường.
- Đã kiểm chứng tự động qua unit test: `tests/test_avatar_female_priority.py` (Passed 100%).

---

## 11. Kiến Trúc Ba Cỗ Máy Song Song (3-Pipeline Parallel Fleet)

1. **Cỗ Máy 1: Render Song Song 2 Workers (`run_render_group3.py`)**:
   - Quét các folder đã nạp đủ >= 20 video gốc, render liên tục 2 luồng FFmpeg ra `D:\TIKTOK-videonuoinick\<folder>`.
2. **Cỗ Máy 2: Tải Đa Luồng 20 Workers Qua Proxy (`smart_gaixinh_distributor.py`)**:
   - Tải song song 20 video từ manifest TikTok gái xinh qua 57 proxy xoay tua, tự động lọc qua AI ViT và cắt lát 45 video (video 46+ đẩy sang bể gộp).
3. **Cỗ Máy 3: Cào Douyin Đa Nhiệm 10 Workers (`douyin_feed_ai_crawler.py`)**:
   - Kết nối Chrome CDP port 9222 lấy cookie sống của Douyin, kéo 10 workers song song qua `f2`, thẩm định bằng AI Whisper Audio Gate (loại bỏ tiếng Trung) và AI ViT Vision.

---

## 12. Quy Tắc Đổi Nguồn Video & Khóa Thứ Tự Render (User Invariant 2026-09-24)

> 📌 **Tham khảo chi tiết chiến lược chuyển đổi Niche & Xử lý Video cũ**: Xem `references/niche-transition-and-cadence-depletion-strategy.md` (giải mã nhịp cạn kho 3.31 ngày/clip, trần 250 follow do gate 6 video, và lý do không bắt buộc ẩn video cũ khi đổi sang gái xinh).

### Bối cảnh & Yêu cầu sống còn
Khi một tài khoản TikTok đang nuôi cần đổi sang nguồn video mới (ví dụ đổi chủ đề, thay kênh nguồn độc quyền):
- Tài khoản đã đăng $N$ video trước đó (ví dụ: `Video Đã Đăng = 3` trên workbook Excel).
- **CẤM TUYỆT ĐỐI**: Reset cột `Video Đã Đăng` về `0` trong Excel!
- **Lý do**: Khi bot upload video chạy, nó tự động đọc `Video Đã Đăng = N` và bốc video kế tiếp là $N + 1$ (ví dụ: $3 + 1 = 4$).
- **QUY CHUẨN THỰC THI**:
  1. **Bảng tính (Workbook Tik*.xlsx)**: Giữ nguyên `Video Đã Đăng = N` (không đụng vào mốc này).
  2. **Thư mục Render (`D:\TIKTOK-videonuoinick\<folder>`)**:
     - Dọn sạch các file video cũ.
     - Khi render từ nguồn mới sang, **bắt buộc đánh số thứ tự bắt đầu từ $N + 1$** bằng cờ `--start-seq <N+1>` trong `random_batch_render.py` (ví dụ: `--start-seq 4` để xuất ra `4.mp4`, `5.mp4`, ..., `43.mp4`).
     - Trong thư mục render mới tuyệt đối không có các file từ `1` đến $N$ (vì những số này bot đã đăng từ nguồn cũ rồi).
  3. Lần chạy batch kế tiếp, bot sẽ bốc chuẩn xác file $N+1$ mới tinh để đăng tiếp mà không bị trùng hay lệch mốc.

---

## 13. Cạm Bẫy Kênh Cosplay Anime, Phim Ngắn & Tiêu Chuẩn Kênh Ít Viral (User Directive 2026-09-24)

### Cạm bẫy phân loại AI Vision với Cosplay Anime / Phim Ngắn
- **Hiện tượng**: Kênh được AI Vision (`AIFemaleFilter`) chấm điểm nữ rất cao (95% - 98%), nhưng khi trích xuất video hoặc avatar thì nhìn như nhân vật hoạt hình / anime.
- **Nguyên nhân cốt lõi**:
  - Model ViT Image Classification chỉ là phân loại nhị phân Nữ (`female`) vs Nam (`male`).
  - Khi gặp video nhân vật nữ trong game (ví dụ: Sangonomiya Kokomi trong Genshin Impact), hoặc bạn nữ cosplay đội tóc giả màu sắc, trang điểm phong cách anime, AI vẫn phân loại là "Nữ" (`female_prob > 0.90`).
  - Ngoài ra, các kênh reup trích đoạn phim ngắn tình cảm Trung Quốc (`#phimngandouyin`, `#phimtrungquoc`) cũng bị lọt vào bể video.
- **Biện pháp phòng ngừa triệt để**:
  1. **Lọc từ khóa Metadata (yt-dlp title & tags)**:
     - Tự động loại trừ các video chứa tag: `#cosplayer`, `#cosplay`, `#hoathinh`, `#anime`, `#genshin`, `#phimngandouyin`, `#phimtrungquoc`, `#reviewphim`.
  2. **Tiêu chuẩn kênh ít viral (Low-viral Personal Creator Invariant)**:
     - **CẤM CHỌN IDOL QUỐC DÂN / QUÁ NỔI TIẾNG**: Tránh các tài khoản idol hàng triệu follow như Khánh Huyền (`@vtkh2004`), Lê Bống (`@lebong95`) vì độ nhận diện quá cao, ai nhìn vào cũng biết là kênh reup.
     - **Ưu tiên kênh cá nhân vừa và nhỏ (~10k - 200k followers)**: Điển hình như `@diepyenvy55` (Diệp Yến Vy). Video tự quay đời thường, đi biển, cafe, nhảy trend nhẹ nhàng, người thật 100%, nuôi nick an toàn và không bị chú ý.

---

## 14. Kỹ Thuật Trích Xuất Avatar Khuôn Mặt Người Thật Rõ Nét (Tránh Avatar Tối Đen / Không Người)

### Triệu chứng & Cạm bẫy
- Lệnh trích xuất ffmpeg theo giây cố định (ví dụ: `-ss 00:00:03` hoặc `-ss 00:00:04`) dễ cắt trúng:
  1. Khung hình chuyển cảnh (fade out / black screen) có độ sáng Mean BGR cực thấp (~20 - 30), tạo ra avatar gần như đen xì.
  2. Khung hình quay cảnh vật, bờ biển, đường phố không có mặt người.
- Hậu quả: User phản ánh "ava gì lạ thế có thấy người trong ava đâu".

### Tiêu chuẩn kỹ thuật tạo Avatar tự động
Bắt buộc áp dụng thuật toán lọc đa tầng:
1. **Quét Face Detection (OpenCV / Haar Cascade / RetinaFace)**:
   - Dò qua các mốc thời gian (1s, 2s, 3s, 5s) của 3-5 video đầu trong thư mục nguồn.
   - Bắt buộc phải phát hiện đúng **1 khuôn mặt người thật** (`minSize=(100, 100)`).
2. **Kiểm tra độ sáng (Brightness Gate)**:
   - ROI khuôn mặt và toàn frame phải đạt độ sáng trung bình trong khoảng `80 <= mean_brightness <= 190`.
   - Loại bỏ hoàn toàn các khung hình tối đen (`< 60`) hoặc cháy sáng (`> 220`).
3. **Cắt khung vuông trung tâm mặt**:
   - Lấy tâm khuôn mặt `(cx, cy)`, mở rộng tỷ lệ `1.8x - 2.0x` kích thước mặt để lấy trọn vẹn cả đầu và tóc.
   - Resize chuẩn `(512, 512)` chất lượng cao Lanczos4 trước khi lưu file `avatar.jpg`.

---

## 15. TikTok 47.x Profile Avatar Edit UI: Icon Bút Chì Góc Trái & Né Bẫy Màn "Thêm Vào Nhật Ký"

### Bối cảnh thay đổi giao diện TikTok 47.x (Samsung S7 / 1080x1920)
- **Cạm bẫy màn "Thêm vào Nhật ký" (Story Picker)**:
  - Trên giao diện mới, bấm trực tiếp vào vòng tròn avatar trên trang Profile sẽ mở ra màn hình **"Thêm vào Nhật ký"** (Story photo/video picker) thay vì mở chức năng đổi avatar.
  - Nếu bot tiếp tục chọn ảnh và lưu ở màn này, ảnh sẽ bị đăng thành **Story 24h** chứ không đổi avatar trang cá nhân!
- **Nút mở "Sửa hồ sơ" chuẩn xác**:
  - Giao diện mới thay thế nút chữ "Sửa hồ sơ" bằng **Icon Bút Chì góc trên bên trái** header Profile.
  - Tọa độ bounds: `[24,96][126,204]`, tâm click: `(75, 150)`.
- **Quy trình đổi Avatar tự động chuẩn TikTok 47.x**:
  1. Tại Profile, tap icon Bút Chì `(75, 150)` -> Mở màn hình **"Sửa hồ sơ"** (`com.ss.android.ugc.aweme.profile.ui.HeaderDetailEditActivity`).
  2. Tap vòng tròn avatar "Thay đổi ảnh" tại tâm `(540, 400)`.
  3. Chọn mục **"Tải ảnh lên"** tại `(400, 1570)`.
  4. Trong thư viện ảnh (Picker), chọn ảnh `avatar.jpg` đầu tiên `(137, 355)` -> Bấm **"Tiếp"** `(912, 1842)`.
  5. Tại màn hình xác nhận, bấm **"Tiếp (1)"** `(912, 1842)` -> Chuyển sang màn hình Cắt ảnh (Crop).
  6. **QUAN TRỌNG**: Đảm bảo checkbox *"Đăng ảnh này lên Nhật ký"* không bị tick (`checked=false`).
  7. Bấm nút **"Lưu"** tại `(792, 1794)`.
  8. Bấm phím Back (KEYCODE_BACK) về lại Profile, chụp ảnh màn hình nghiệm thu visual avatar mới.

---

## 16. Chặn Triệt Để Anime, Hoạt Hình 3D, Game & Clip Tào Lao Từ Douyin (Zero-Junk Invariant)

### Bối cảnh cạm bẫy từ khóa và feed Douyin
Feed thịnh hành tổng hợp (`/jingxuan`) của Douyin chứa đầy nội dung không liên quan đến gái xinh: hoạt hình Khủng long sữa (`奶龙`), phim hoạt hình AI (`#ai漫剧`), review điện thoại (`小白测评`), game Liên Quân, PUBG...
Nếu chỉ dựa vào cào feed ngẫu nhiên thì tỷ lệ rác rất cao, làm người dùng bực mình ("Douyin tải gái thôi đấy nhé đừng có anime vs tào lai").

### Cơ chế 3 tầng phòng thủ chống Junk & Anime (Bao gồm BJD, Thủ Công & Cosplay)
1. **Tiền lọc từ khóa tiếng Trung trước khi tải (`DOUYIN_BLACKLIST_KEYWORDS`)**:
   - Danh sách từ khóa rác bắt buộc chặn (bao gồm hoạt hình, game, review, BJD doll, đất sét thủ công, ăn giả, cosplay):
     ```python
     DOUYIN_BLACKLIST_KEYWORDS = [
         "动漫", "动画", "二次元", "漫剧", "ai漫剧", "ai动画", "ai画",
         "游戏", "王者", "吃鸡", "原神", "无畏契约", "我的世界", "英雄联盟",
         "段子", "搞笑", "电影", "影视", "解说", "纪录片", "美食", "做饭",
         "萌宠", "奶龙", "奥特曼", "小猪佩奇", "沙雕", "测评", "数码", "车",
         "粘土", "手工", "bjd", "钥匙扣", "排球少年", "假吃", "谷子", "cos", "cosplay"
     ]
     ```
   - **Cạm bẫy BJD Doll & Thủ công / Ăn giả ("假吃")**:
     * Các kênh làm đồ chơi đất sét, búp bê BJD thường có nickname chứa chữ `baby`, `酱`, `yuki` nên dễ bị sitemap bốc nhầm.
     * Khuôn mặt búp bê BJD có mắt to, môi son khiến model ViT phân loại nhầm thành "Nữ thật" (`score > 85%`).
     * Tương tự, bạn nữ cosplay đội tóc giả màu sắc sặc sỡ hoặc đeo phụ kiện anime nhân vật game (`#无期迷途`, `#cos`) cũng bị AI chấm điểm nữ cao.
     * **Bắt buộc**: Kiểm tra tên file / tiêu đề video tải về qua `DOUYIN_BLACKLIST_KEYWORDS`. Hễ dính bất kỳ từ khóa nào trên là `[BLACKLIST REJECT]` xóa ngay lập tức trước khi chuyển sang bước duyệt âm thanh/lưu kho.
2. **Nâng ngưỡng AI ViT lên `≥ 75%` (Real Human Female Gate)**:
   - Các nhân vật 3D, filter biến hình hoạt hình hay AI vẽ thường chỉ đạt độ tin cậy bạn nữ người thật từ 50%–70%.
   - Nâng ngưỡng lên `score >= 0.75` trong `download_and_verify_douyin` đảm bảo 100% video giữ lại là **bạn nữ người thật bằng xương bằng thịt**.
3. **Bộ lọc Whisper Audio Gate**:
   - Loại bỏ 100% video có tiếng nói tiếng Trung, chỉ giữ lại các clip thuần nhạc nền / dance / OOTD.

---

## 17. Nghiệm Thu Hình Ảnh Qua Contact Sheet / Grid Preview Trong Môi Trường Headless

### Vấn đề
Khi người dùng yêu cầu chụp ảnh màn hình các folder video ("Chụp ảnh mấy folder đó đây t xem. Vì đã có preview nên nhìn qua xem"), nếu terminal agent chạy trong console dịch vụ Windows không tương tác (Session 0 hoặc non-interactive shell), lệnh `CopyFromScreen` của .NET hoặc `ImageGrab.grab()` sẽ văng lỗi `The handle is invalid` / `screen grab failed`.

### Giải pháp kỹ thuật: Contact Sheet / Grid Generator
Dùng trực tiếp FFmpeg trích xuất khung hình ở giây thứ 2 của 12–16 video đầu tiên trong folder, sau đó dùng PIL ghép thành một ảnh lưới (Grid Image) kích thước lớn:
```python
def generate_folder_grid(folder_path, out_png, grid_cols=4, grid_rows=3):
    files = [f for f in os.listdir(folder_path) if f.endswith('.mp4')][:grid_cols * grid_rows]
    thumb_w, thumb_h = 240, 360
    grid_img = Image.new('RGB', (grid_cols * thumb_w, grid_rows * thumb_h), (30, 30, 30))
    for idx, f in enumerate(files):
        p = os.path.join(folder_path, f)
        frame_tmp = f"tmp_{idx}.jpg"
        subprocess.run(['ffmpeg', '-y', '-ss', '00:00:02', '-i', p, '-vframes', '1',
                        '-vf', f'scale={thumb_w}:{thumb_h}:force_original_aspect_ratio=decrease,pad={thumb_w}:{thumb_h}:(ow-iw)/2:(oh-ih)/2',
                        frame_tmp], capture_output=True)
        if os.path.exists(frame_tmp):
            img = Image.open(frame_tmp)
            grid_img.paste(img, ((idx % grid_cols) * thumb_w, (idx // grid_cols) * thumb_h))
            os.remove(frame_tmp)
    grid_img.save(out_png)
```
- Ảnh xuất ra (`grid_folder_<N>.jpg`) hiển thị đồng thời 12 video dạng lưới giống hệt chế độ xem Extra Large Icons của Windows Explorer.
- Đính kèm `MEDIA:/path/to/grid_folder_<N>.jpg` gửi qua Telegram, thỏa mãn 100% Gate 6 (Visual Evidence) mà không phụ thuộc vào trạng thái màn hình desktop của host.

---

## 18. Khác Biệt Cốt Lõi Douyin Web vs Mobile App & WebSocket CDP Client Trap

### Bản chất Feed Douyin Web (Jingxuan Desktop Feed Trap)
- **Hiện tượng**: Khi cào feed Douyin từ Chrome CDP (`https://www.douyin.com/jingxuan` hoặc `/jingxuan/beauty`), 95% video tải về bị AI Whisper / AI ViT đánh trượt và xóa sạch.
- **Nguyên nhân cốt lõi**:
  - ByteDance định vị bản web `douyin.com` trên PC là **nền tảng video dài (dạng YouTube / Bilibili)**.
  - Các bài đăng thịnh hành trên feed web hầu hết là:
    * Phim tài liệu lịch sử 30–45 phút (ví dụ: *全斗焕 33:50*).
    * Phim hoạt hình dài tập 40 phút (*我体内有颗神秘种子 40:43*).
    * Review đồ ăn, công nghệ 42 phút (*全国84款地方特色月饼 42:49*).
    * Phim ngắn AI 45 phút (*原创AI悬疑剧 45:37*).
  - Đây **KHÔNG PHẢI** là feed video dọc ngắn 15–30s như trên app điện thoại di động!
- **Chiến lược khai thác chuẩn xác**:
  1. **Nguồn Kênh Cá Nhân (Creator Profile)**: Lấy link chia sẻ từ app điện thoại (`https://v.douyin.com/...` hoặc `https://www.douyin.com/user/<sec_uid>`). Chạy `f2 dy -M post -o 40` để kéo trọn bộ video ngắn của riêng bạn nữ đó.
  2. **Nguồn Kênh Tuyển Chọn (Curated Douyin Hubs)**: Khai thác các kênh trên TikTok chuyên tuyển chọn video ngắn Douyin visual cao (`source_manifest_gaixinh.jsonl`). Đây là cách đạt sản lượng cao nhất và ổn định nhất cho phone farm quy mô lớn.

### Kỹ thuật giao tiếp Chrome CDP: Thư viện `websockets.sync.client`
- Tránh dùng raw TCP socket tự ghép frame websocket vì dễ dính lỗi phân mảnh frame và timeout vô tận khi tải DOM lớn.
- Sử dụng `from websockets.sync.client import connect` để thực thi lệnh CDP đồng bộ, tốc độ phản hồi 0.01s.
- ⚠️ **CẠM BẪY THAM SỐ TIMEOUT CỦA `websockets.sync.client.connect`**:
  * Hàm `connect()` của `websockets.sync.client` **KHÔNG nhận tham số `timeout=...`**!
  * Nếu gọi `connect(ws_url, timeout=5)` -> Bị crash ngay với lỗi: `TypeError: connect() got an unexpected keyword argument 'timeout'`.
  * **Cú pháp chuẩn xác**:
    ```python
    from websockets.sync.client import connect
    with connect(ws_url, open_timeout=5, close_timeout=5) as ws:
        ws.send(json.dumps({"id": 1, "method": method, "params": params or {}}))
        resp = json.loads(ws.recv())
    ```

---

## 19. Cấm Bắt User Gửi Link Tiếng Trung & Kỹ Thuật Tự Động Săn Kênh Douyin Qua Sitemap HTML

### Nguyên tắc ứng xử cốt lõi (User Directive 2026-09-25)
- **"User không biết tiếng Trung"**: CẤM TUYỆT ĐỐI Coordinator bắt user đi tìm hoặc gửi link Douyin tiếng Trung ("Mẹ t đã k biết tiếng trung yêu cầu m đi cào cho t m lại bảo t gởi link cái cc à").
- **Kỷ luật tự chủ**: Nhiệm vụ của Agent là phải tự động hóa 100% việc săn kênh, lấy ID, lọc nội dung và kéo video về. User chỉ việc nhận kết quả và kiểm tra ảnh/video nghiệm thu.

### Kỹ thuật tự động bóc tách Profile Douyin qua Sitemap HTML (`htmlmap`)
- Khi trang tìm kiếm web (`douyin.com/search`) bị chặn bởi WAF / Captcha iframe (`rc-verifycenter`) hoặc yêu cầu đăng nhập QR:
  - Douyin cung cấp sitemap công khai rất lớn phục vụ SEO tại:
    * `https://www.douyin.com/htmlmap/hotauthor_0_{page}` (1..50)
    * `https://www.douyin.com/htmlmap/douauthor_0_{page}` (1..50)
    * `https://www.douyin.com/htmlmap/hotchallenge_0_{page}` (1..50)
  - Các trang này trả về HTML tĩnh chứa hàng nghìn link tác giả chuẩn:
    `\"entityName\":\"...\",\"linkUrl\":\"https://www.douyin.com/user/MS4wLjABAAAA...\"`
  - Dùng `ThreadPoolExecutor` quét đồng thời 20 trang sitemap, lọc `entityName` theo từ khóa hot girl / dance:
    * Positive keywords: `['穿搭', '学姐', '甜妹', '变装', '纯欲', 'yuki', 'nana', 'baby', 'dance', '跳舞', '街拍', '模特', '女神']`.
    * Negative keywords: `['机构', '培训', '少儿', '招生', '教育', '器材', '广场舞', '剧', '电影', '公司', '官方', '游戏', '男', '车']`.
  - Kết quả: Thu thập được danh sách 40–100 bạn nữ Douyin thật (`douyin_hot_girls.json`) hoàn toàn tự động chỉ trong 2 giây mà không cần nhờ user hay vượt captcha.

---

## 20. Cạm Bẫy Treo Timeout 30s Của Tool `f2` (Bark Push Notification Trap & Fix)

### Hiện tượng
Khi chạy lệnh tải video Douyin bằng `f2`:
`f2 dy -u <url> -M one -k <cookie> -p <output_dir>`
Tiến trình bị đơ/chậm mất đúng 30 giây cho mỗi video trước khi tải hoặc báo timeout, dù mạng bình thường.

### Nguyên nhân gốc rễ
- File cấu hình mặc định của thư viện `f2` (`.../site-packages/f2/conf/conf.yaml`) đặt `enable_bark: true`.
- `Bark` là dịch vụ gửi push notification lên iPhone (`https://api.day.app/`).
- Do người dùng không cấu hình Bark key, mỗi khi `f2` bắt đầu xử lý tác phẩm, nó sẽ gửi HTTP POST đến `https://api.day.app/`.
- Server Day.app trả về lỗi `HTTP 405 Method Not Allowed`, khiến `f2` retry và treo kết nối mạng trong 15–30s:
  ```text
  ERROR HTTP状态错误：Client error '405 Method Not Allowed' for url 'https://api.day.app/'
  ERROR Bark 通知发送失败，请检查 key 和网络连接
  ```

### Cách khắc phục triệt để
Sửa file cấu hình `conf.yaml` của `f2`:
Đường dẫn trên Windows: `<python_env>/Lib/site-packages/f2/conf/conf.yaml`
```yaml
f2:
  version: "0.0.1.7"
  show_update: true
  enable_bark: false  # BẮT BUỘC ĐỔI THÀNH FALSE
```
Sau khi sửa, `f2` không còn gọi push notification, tốc độ tải video trở lại bình thường (1–2 giây/video).

---

## 21. Quy Trình Cào Hàng Loạt Douyin Tự Động (`auto_douyin_girls_downloader.py`)

- **Kịch bản thực thi**: `D:/Taadaa/Tiktok-video/scripts/auto_douyin_girls_downloader.py`
- **Quy trình chuẩn**:
  1. Đọc danh sách creators từ `D:/Taadaa/Tiktok-video/data/douyin_hot_girls.json`.
  2. Lấy cookie sống từ `cookie_string.txt` (Chrome CDP 9222).
  3. Duyệt từng kênh tác giả, gọi `f2 dy -u <c_url> -M post -o 5 -k <cookie>` tải 5 video mới nhất.
  4. Hậu kiểm 2 tầng AI:
     - **AI Vision ViT**: Nữ thật `score >= 0.70`.
     - **AI Whisper**: Thuần BGM `verify_audio_no_speech`, xóa ngay lập tức nếu phát hiện `zh_speech`.
  5. Đạt chuẩn -> Lưu vào thư mục đích `C:/Users/Kibe/AppData/Local/hermes/evidence/douyin_verified_girls/`.
- **Kỷ luật báo cáo tiến độ**: Khi các đợt tải 20 workers hoặc render hoàn thành, Coordinator bắt buộc phải chủ động thông báo rõ ràng số lượng folder và video đã đạt mốc trên đĩa (tránh tình trạng tiến trình chạy ngầm xong nhưng im lặng khiến user tưởng hệ thống bị dừng hoặc lỗi).

---

## 22. Quy Trình Mở Rộng Quy Mô Lớn (Scaling Video Sourcing > 27 Folders)

### Bối cảnh 80 Máy / Dàn
- Mỗi bảng tính Tik (ví dụ: `Tik7.xlsx`) quản lý 80 máy với 80 folder video riêng biệt (`Folder Video = (Máy - 1)*8 + Slot_Index`).
- Đợt triển khai ban đầu (27 folder) chỉ bao gồm các máy cần ưu tiên chuyển đổi (Group 1: 5 máy, Group 2: 9 máy, Group 3: 13 máy).
- Khi mở rộng quy mô lên toàn bộ 80 máy (53 folder còn lại) hoặc mở rộng sang các workbook khác (`Tik1..Tik8`):
  1. **Thách thức cạn nguồn kênh (Manifest Depletion)**:
     - Với cơ chế Claim độc quyền (`gaixinh_channel_claims.json`), 15–18 kênh trong `source_manifest_gaixinh.jsonl` sẽ nhanh chóng bị chiếm hết sau 25–30 folder.
  2. **Giải pháp Đa Nguồn Kết Hợp (Multi-Source Scaling)**:
     - Nguồn TikTok: Bổ sung kênh mới qua discovery tự động hoặc các kênh curation lớn.
     - Nguồn Douyin: Sử dụng danh sách 40–100 tác giả đã trích xuất từ sitemap Douyin (`data/douyin_hot_girls.json`).
     - Chia thành các nhóm cuốn chiếu (Batch 15–20 folders): Tải xong nhóm nào kích hoạt render 2 workers nhóm đó ngay lập tức, đảm bảo luồng sản xuất liên tục không bị nghẽn đĩa hay cạn kênh.

---

## 23. Kỷ Luật Giám Sát Worker & Hậu Kiểm Độc Quyền File Code Trên Đĩa

### Hiện tượng & Cạm bẫy
- Khi Coordinator dispatch subagent qua `delegate_task` để sửa code/script (ví dụ: thêm blacklist vào `auto_douyin_girls_downloader.py`), subagent có thể bị timeout (600s) hoặc hoàn thành nhưng không thực hiện ghi đĩa (`0 files modified`).
- Nếu Coordinator chỉ đọc báo cáo hoặc cho rằng tác vụ đã hoàn thành mà không kiểm tra thực tế, lỗi sẽ tồn tại âm thầm trong các lần chạy sau (ví dụ: video rác BJD/đất sét tiếp tục bị tải về máy).

### Quy tắc bất biến (Post-Delegation Verification Invariant)
1. **Kiểm tra trực tiếp file trên đĩa**:
   - Sau khi worker trả kết quả hoặc timeout: Dùng `read_file` hoặc `grep` kiểm tra chuỗi code mới (`DOUYIN_BLACKLIST_KEYWORDS`, v.v.) có thực sự nằm trong file hay chưa.
2. **Kiểm tra cú pháp độc lập**:
   - Bắt buộc chạy `python -m py_compile <path>` ngay tại session Coordinator để xác nhận exit code 0.
3. **Báo cáo tiến trình nền chủ động**:
   - Khi các background job (như tải 20 workers, render 2 workers) hoàn thành: BẮT BUỘC kiểm tra số lượng file trên `D:\video goc` và `D:\TIKTOK-videonuoinick`, gửi bảng tổng kết thực tế cho người dùng ngay, tuyệt đối không im lặng.
4. **Không nhờ User tìm/check link Douyin**:
   - User không biết tiếng Trung; cấm tuyệt đối hỏi xin link hay yêu cầu user check profile tiếng Trung thủ công.
   - Toàn bộ khâu săn kênh, bóc tách sitemap Douyin, kiểm định AI ViT + Whisper phải tự động hóa 100%.

---

## 24. Mở Rộng Dàn Admin Qua Bắn SSH (`admin-farm` 192.168.110.119) & Phối Hợp Kibe - Admin

### Bối cảnh & Hiện trạng hai máy Farm
1. **Host Kibe (Local)**:
   - Quản lý các dàn `Tik1..Tik8` nhánh Kibe (`D:\OneDrive\TaadaaData\kibe\Tik*.xlsx`).
   - Thư mục video gốc: `D:\video goc\<folder>` (đã nạp 640 folders).
   - Thư mục video render: `D:\TIKTOK-videonuoinick\<folder>` (640 folders).
   - Tiến độ dàn Tik7: 27 folder ưu tiên đã render xong 100% (1.074 video MP4), 53 folder còn lại đang chứa niche cũ và chờ nạp gái xinh cuốn chiếu.
   - Trạng thái Tik8: 80 máy mới đăng tối đa 0–3 video (14 máy 0 clip, 31 máy 1 clip, 32 máy 2 clip, 3 máy 3 clip). An toàn tuyệt đối để nạp video và render từ `N + 1`.
2. **Host Admin (`admin-farm` / 192.168.110.119 / User: Admin)**:
   - Kết nối SSH không password qua private key `~/.ssh/id_ed25519_kibe_admin`.
   - Quản lý các dàn `Tik1..Tik8` nhánh Admin (`D:\OneDrive\TaadaaData\admin\Tik*.xlsx`).
   - Thư mục video gốc: `D:\video goc may 2\<folder>` (640 folders).
   - Thư mục video render: `D:\TIKTOK-videonuoinick-admin\<folder>` (453 folders).
   - Trạng thái Tik8 Admin: 100% 80 máy có `Video Đã Đăng = 0` (chưa từng đăng video nào).
   - **Giới hạn ổ đĩa Admin**: Ổ `D:\` của Admin còn trống ~26.3 GB. Bắt buộc bắn tải cuốn chiếu theo batch nhỏ (20–30 folders/lần) để tránh tràn đĩa.

## 25. Cạm Bẫy Định Danh File Tải F2 Douyin & Quét File Trên Windows

### Triệu chứng & Vấn đề
1. File tải về từ `f2` mặc định định dạng `naming: '{create}_{desc}'` trong `app.yaml`:
   - Tiêu đề Douyin (`desc`) thường chứa emoji, ký tự lạ tiếng Trung hoặc quá dài (> 200 ký tự).
   - Trên Windows NTFS, độ dài đường dẫn vượt quá `MAX_PATH` (260 ký tự) hoặc chứa ký tự đặc biệt sẽ gây lỗi crash: `No such file or directory` hoặc `ls: cannot access ...: Invalid or incomplete multibyte or wide character`.
   - Lệnh `Path.rglob('*.mp4')` hoặc `os.walk` bị crash hoặc quét đĩa diện rộng vi phạm Farm Invariant.
2. Lưu nhầm ổ đĩa C:
   - Thư mục tạm mặc định trong script nếu trỏ vào `C:\Users\Kibe\AppData\Local\...` sẽ làm đầy ổ hệ điều hành (`C:\`).

### Quy chuẩn khắc phục triệt để
1. **Chuẩn hóa đặt tên file `f2`**:
   - Sửa cấu hình `.../site-packages/f2/conf/app.yaml`:
     ```yaml
     douyin:
       naming: '{create}_{aweme_id}'  # BẮT BUỘC: chỉ dùng timestamp + video ID số
     ```
   - Tên file sinh ra sẽ cực kỳ ngắn gọn và an toàn: `2026-09-01 13-35-03_7680436188561921704_video.mp4`.
2. **Quy định đường dẫn ổ đĩa D**:
   - Toàn bộ video raw, temp và cache của quy trình cào Douyin bắt buộc trỏ trực tiếp vào ổ `D:\video goc\` (ví dụ: `D:\video goc\douyin_temp`, `D:\video goc\douyin_verified_girls`).
3. **Duyệt file an toàn không dùng `rglob`**:
   - Đọc trực tiếp thư mục cấp tác giả `author_dir = c_temp / "douyin" / "post"` bằng `iterdir()` 1 cấp, tránh hoàn toàn đệ quy sâu.

1. **Đồng bộ Dependencies & Model trước khi chạy**:
   - Máy Admin có thể thiếu các thư viện Python hoặc model ViT ONNX mới:
     ```bash
     scp -q "D:/Taadaa/Tiktok-video/scripts/smart_gaixinh_distributor.py" "D:/Taadaa/Tiktok-video/scripts/ai_channel_filter.py" "D:/Taadaa/Tiktok-video/scripts/gaixinh_claims.py" admin-farm:"D:/Taadaa/Tiktok-video/scripts/"
     scp -q "D:/Taadaa/Tiktok-video/data/source_manifest_gaixinh.jsonl" "D:/Taadaa/Tiktok-video/proxy_pool_67.txt" admin-farm:"D:/Taadaa/Tiktok-video/data/"
     scp -q "D:/Taadaa/Tiktok-video/models/onnx/model_quantized.onnx" admin-farm:"D:/Taadaa/Tiktok-video/models/onnx/"
     ssh admin-farm "powershell.exe -NoProfile -Command \"& 'C:\\Users\\Admin\\AppData\\Local\\hermes\\hermes-agent\\venv\\Scripts\\python.exe' -m pip install numpy onnxruntime Pillow yt-dlp\""
     ```
2. **Cạm bẫy Unicode & PowerShell Escape qua SSH Windows**:
   - Khi truyền lệnh PowerShell phức tạp có chứa đường dẫn có dấu cách (`D:\video goc may 2`), escape lồng nhau giữa Bash/MSYS và PowerShell rất dễ văng lỗi `SyntaxError: unicodeescape` hoặc `PositionalParameterNotFound`.
   - Lệnh in `--help` hoặc chạy Python với chuỗi tiếng Việt trên Windows console Admin sẽ văng lỗi:
     `UnicodeEncodeError: 'charmap' codec can't encode character ... character maps to <undefined>`.
   - **Giải pháp chuẩn xác**:
     * Luôn set biến môi trường UTF-8: `$env:PYTHONUTF8='1'`.
     * Tạo file `.bat` local (`run_admin_download.bat`), scp sang Admin rồi thực thi file thông qua `Start-Process -FilePath ... -WindowStyle Hidden` để tiến trình sống ngầm hoàn toàn độc lập với phiên SSH.
## 26. Quy Tắc Báo Cáo Định Kỳ 6 Giờ / Lần (6-Hour Periodic Farm Report Invariant)

### Bối cảnh & Yêu cầu của User (Cập nhật 2026-10-07)
- Khi thực thi các chiến dịch tải, render và cào video quy mô lớn (hàng chục đến hàng trăm folder, hàng nghìn video):
  - Trước đây cấu hình 1 giờ/lần gây loãng và spam thông báo liên tục.
  - User ra chỉ thị chuẩn hóa: **"Báo 6 tiếng 1 lần thôi"**.
- **Cơ chế thiết lập chuẩn xác**:
  1. **Tối ưu hóa Watchdog kiểm đếm**:
     - File `farm_render_download_watchdog.py` dùng `wmic process where "name='python.exe' or name='ffmpeg.exe'" get commandline` (tốc độ < 0.2s).
     - Kiểm đếm dữ liệu video gốc và render ưu tiên đọc từ `C:\CodexRuntime\tiktok-video\state.db` (5ms) và `os.scandir` phân cấp nhanh (0.12s), không quét đĩa sâu.
  2. **Cấu hình CronJob 6 Giờ / Lần**:
     - Job: `farm-render-download-watchdog` (Job ID: `9c7a147d48b8`).
     - Schedule: `0 */6 * * *` (vào các khung giờ `00:00`, `06:00`, `12:00`, `18:00`).
     - Deliver: `origin` (bắn thẳng vào khung chat Telegram).
     - Nội dung: Thống kê chi tiết số video gốc (`D:\video goc`), số video render (`D:\TIKTOK-videonuoinick`), trạng thái 8 dàn Tik1..Tik8 và tổng video thành phẩm toàn farm. Không bắn dày 1h/lần nữa.

---

## 27. Kỷ Luật Nạp Gối Đầu Khi Cạn Kho & Báo Cáo Hết Video Watchdog (User Directive 2026-10-01)

### 1. Nguyên tắc cùng chủ đề khác nhân vật & cấm ép đổi niche ẩn video
- **Cùng chủ đề nhưng khác nhân vật**: Hoàn toàn hợp lệ và tự nhiên. Kênh thú cưng, mẹo vặt, đời sống, hài hước hay gái xinh bản chất là Theme Page / Curated Hub; khán giả xem và follow theo từng clip ngắn trên FYP chứ không soi lịch sử 40 clip xem có cùng 1 con vật hay 1 nhân vật hay không.
- **CẤM đổi niche rồi ép ẩn video cũ**: Giữ nguyên toàn bộ video cũ để duy trì độ dày lịch sử tài khoản, tương tác và view thụ động. Không thao tác thừa trên account.

### 2. Kỷ luật cảnh báo cạn kho (Zero Early Warning Invariant)
- **CẤM cảnh báo sớm khi còn <= 5 video**: Không làm loãng thông tin của User bằng các cảnh báo dự báo thừa thãi.
- **CHỈ BÁO KHI THỰC SỰ HẾT VIDEO**: Khi nick đã đăng hết video trong folder render và upload runner gặp `video_not_rendered`, bot upload tự động skip an toàn (không lỗi app, không dừng phiên lướt feed).
- **Tích hợp dòng báo cáo chuyên biệt trong Watchdog (`feed_session_watchdog.py`)**:
  - Khi có máy cạn kho, báo cáo ca nuôi acc tự động xuất dòng:
    ```text
    + Hết video/Cần cào (N): M21, M38...
    ```
  - Khi thấy dòng này, người vận hành chỉ cần cào thêm 40 clip mới cùng chủ đề nạp gối đầu và render nối tiếp `--start-seq <N+1>` để bot tự động bốc tiếp video mới đăng mượt mà.






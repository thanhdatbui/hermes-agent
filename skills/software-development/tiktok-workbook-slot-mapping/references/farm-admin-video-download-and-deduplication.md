# Farm Admin Video Download & Deduplication Architecture (D:/video goc may 2)

## 1. Bối cảnh & Nguyên tắc Tối cao
Farm Taadaa vận hành 2 cụm máy độc lập:
- **Cụm Kibe (Máy 1 - 80)**: Lưu trữ video gốc tại `D:/video goc`, render tại `D:/TIKTOK-videonuoinick`.
- **Cụm Admin (Máy 201 - 280)**: Lưu trữ video gốc tại `D:/video goc may 2`, render tại `D:/TIKTOK-videonuoinick-admin`.

### Bất biến vận hành (Hard Invariants):
1. **TIÊU CHUẨN NGUỒN VIDEO & ĐỊNH NGHĨA "NICHE HOT VIEW" (KHÔNG CÓ TIẾNG NÓI NƯỚC NGOÀI)**:
   - **Cốt lõi:** TUYỆT ĐỐI KHÔNG CÓ TIẾNG NÓI NƯỚC NGOÀI (Cấm có voiceover, tiếng người xì xồ tiếng Trung, tiếng Anh hay ngôn ngữ ngoại lai gây lộ nick clone/reup).
   - **Các nhóm nội dung được phép & ưu tiên cao:**
     * **Douyin Gái Xinh thuần visual / biến hình / nhảy trend:** Chỉ có nhạc nền bắt tai hoặc sound trend, KHÔNG CÓ LỜI THOẠI TIẾNG TRUNG $\rightarrow$ Giữ chân người xem tốt, cắn đề xuất mạnh tại thị trường VN.
     * **Oddly Satisfying & ASMR:** Cắt xà phòng, cắt cát động lực, ép thủy lực, tiếng động vật lý tự nhiên $\rightarrow$ 100% không tiếng người nói, không rào cản ngôn ngữ, retention rate kịch trần.
     * **Gái Xinh & Creator cá nhân Việt Nam:** Nhảy trend nhẹ nhàng, đời thường, nhạc TikTok Việt. BẮT BUỘC chọn kênh quy mô vừa/nhỏ, KHÔNG ĐƯỢC CHỌN IDOL TRIỆU FOLLOW (tránh các KOL như Ngọc Kem, Lê Bống vì quá quen mặt, dễ bị quét clone và dính gậy bản quyền).
     * **Thú cưng / Chó mèo hài hước:** Visual cute đời thường, không rào cản ngôn ngữ.
2. **CẤM ĐỤNG HÀNG NỘI BỘ ADMIN (Cross-Folder Deduplication)**:
   - Mỗi folder trong 640 folder nguồn của Admin (`1..640`) bắt buộc phải nhận **đúng 1 kênh độc quyền duy nhất**.
   - CẤM TUYỆT ĐỐI một kênh bị cào lặp lại cho nhiều folder khác nhau.
3. **CẤM ĐỤNG HÀNG VỚI KIBE FARM (Cross-Machine Exclusion)**:
   - Admin farm không bao giờ được cào trùng kênh hoặc trùng video ID với Kibe farm.
   - Đối soát tự động qua danh sách blacklist: `D:/OneDrive/SharedData/tiktok-video/kibe_downloaded_ids.json` (chứa hơn 57.000 video IDs đã tải của Kibe).

---

## 2. Bẫy lỗi thường gặp trên Farm Admin (Root Cause Analysis)

### Bẫy 1: Downloader cũ bị dừng do Timeout & Lỗi lặp Fallback dồn cục
- **Hiện tượng**:
  Khi chạy `run_admin_gaixinh_downloader.py`, tiến trình bị dừng (exit) sau khi gặp các folder bị lỗi timeout 600s.
- **Nguyên nhân gốc rễ**:
  Hàm `extract_candidate_videos` trong `download_gaixinh_pipeline.py` khi gặp kênh bị lỗi hoặc hết video qualified sẽ rơi vào vòng lặp fallback. Do không cập nhật con trỏ kênh, script tự động nhảy về duyệt lại từ đầu file manifest (`source_manifest_viral_rotation.jsonl`), dẫn đến hiện tượng:
  - Kênh `https://www.youtube.com/shorts/YQJvA_R99EA` (`Yêu Lu`) bị cào nhân bản vào **56 folder khác nhau**!
  - Kênh `Vinh Xô Pet` bị nhân bản vào **19 folder**!
  - Kênh `Mèo Hera` vào **8 folder**!
- **Hậu quả**:
  Vừa vi phạm cấm đụng hàng nội bộ, vừa vi phạm cấm đụng hàng với Kibe (kênh `Yêu Lu` vốn đã được cấp cho Folder 199 bên Kibe).

### Bẫy 2: Lỗi yt-dlp thiếu User-Agent trên Admin
- **Hiện tượng**:
  Khi gọi `yt-dlp` cào TikTok trên Admin, tool ném lỗi:
  ```
  WARNING: [tiktok:user] The extractor is attempting impersonation, but no impersonate target is available.
  ERROR: <username>: Failed to parse JSON (caused by JSONDecodeError)
  ```
- **Nguyên nhân**:
  TikTok chặn request từ yt-dlp chạy mặc định không có User-Agent chuẩn trình duyệt.
- **Giải pháp**:
  Bắt buộc truyền cờ `--user-agent`:
  `--user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"`

### Bẫy 3: Máy Admin thiếu thư viện OpenCV (`cv2`) khi tạo Avatar
- **Hiện tượng**:
  Khi gọi `_make_avatar.py` trên Admin, script crash với lỗi:
  ```
  ModuleNotFoundError: No module named 'cv2'
  ```
- **Giải pháp**:
  Dùng trực tiếp FFmpeg native (đã cài sẵn trên Windows path của Admin) để cắt và crop frame avatar chuẩn 512x512:
  ```bash
  ffmpeg -hide_banner -loglevel error -y -ss 00:00:02 -i "1.mp4" -vf "scale=512:512:force_original_aspect_ratio=increase,crop=512:512" -vframes 1 -q:v 2 "avatar.jpg"
  ```

---

## 3. Kiến trúc Cào Sạch & Chuẩn Hóa cho Farm Admin

### 1. Kho nguồn chuẩn 100% Việt Nam:
- **File Manifest**: `D:/Taadaa/Tiktok-video/data/source_manifest_admin_vn.jsonl`
- Được lọc từ 579 kênh TikTok đã kiểm định 100% creator Việt Nam (`verified_vn == True`), loại bỏ hoàn toàn các kênh đã được cấp cho Kibe.
- Bao gồm các ngách đời thường nhiều view:
  * Nấu ăn / Bếp Việt / Ẩm thực đường phố (`bepviet`, `monngon`, `amthuc`)
  * Gái xinh nhảy trend / đời thường Việt Nam (`nhay`, `thoitrang`, `lamdep`)
  * Thú cưng cute Việt Nam (`thucung`, `yeuthucung`)
  * Mẹo đời sống, phát triển bản thân, học sinh, gia đình.

### 2. Sổ cái độc quyền Admin:
- **File Claims**: `D:/Taadaa/Tiktok-video/data/admin_channel_claims.json`
- Ghi nhận `ch_url -> {folder, uploader, claimed_at}` để đảm bảo không một kênh nào bị cấp trùng lần thứ 2.

### 3. Script thực thi chuẩn hóa:
`D:/Taadaa/Tiktok-video/scripts/run_admin_clean_vn_downloader.py`

#### Quy trình 5 bước trong script:
1. **Cách ly & Dọn sạch**: Tự động dọn sạch toàn bộ 88 folder từng bị nhiễm trùng lặp kênh cũ (`INFECTED_FOLDERS`).
2. **Chọn kênh độc quyền 1:1**: Duyệt qua manifest sạch, tìm kênh chưa nằm trong `admin_channel_claims.json`.
3. **Tải qua Proxy MikroTik LAN**: Xoay ngẫu nhiên cổng `10001..10035` (`192.168.110.2`) kèm User-Agent chuẩn.
4. **Chuẩn hóa tên file**: Đổi tên các clip tải về thành `1.mp4, 2.mp4... 40.mp4` (giới hạn đúng 40 video/folder).
5. **Tạo avatar & metadata**:
   - Dùng FFmpeg trích xuất `avatar.jpg` (512x512) tại giây thứ 2 của `1.mp4`.
   - Ghi nhận `channel_info.json` vào folder gốc.
   - Ghi nhận claim vào `admin_channel_claims.json`.

---

## 4. Cách khởi chạy và giám sát trên Farm Admin qua SSH

### Khởi chạy background độc lập:
```bash
ssh admin-farm 'python -' << 'EOF'
import subprocess
p = subprocess.Popen(
    ["python", "D:/Taadaa/Tiktok-video/scripts/run_admin_clean_vn_downloader.py"],
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
)
print("Started Admin Clean VN Downloader PID:", p.pid)
EOF
```

### Giám sát tiến độ:
```bash
ssh admin-farm 'python -' << 'EOF'
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
log_path = "D:/CodexRuntime/tiktok-video/download_clean_vn_admin.log"
with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()
    for l in lines[-15:]:
        print(l.strip())
EOF
```

### Kiểm tra số lượng video gốc đã đạt chuẩn trên Admin:
```bash
ssh admin-farm 'python -' << 'EOF'
from pathlib import Path
video_goc = Path("D:/video goc may 2")
ge40 = len([f for f in range(1, 641) if len([x for x in (video_goc / str(f)).glob("*.mp4")]) >= 40])
print(f"Admin folders with >= 40 mp4: {ge40} / 640")
EOF
```

---

## 5. Sự cố Tràn Ổ Đĩa D: trên Admin Farm (Disk Space Exhaustion / 0 MB Free Out-of-Disk Trap)

### Bối cảnh phần cứng:
- Máy Kibe: Ổ `D:` dung lượng **4 TB** (trống > 1.6 TB) $\rightarrow$ chứa thoải mái cả video gốc lẫn video render.
- Máy Admin: Ổ `D:` dung lượng chỉ có **1 TB (931 GB khả dụng)**.

### Triệu chứng & Nguyên nhân gốc rễ:
- Khi tiến trình Render thành phẩm (`D:/TIKTOK-videonuoinick-admin`) đạt 482 folders (~21.500 clip) chiếm **521 GB**, kết hợp với kho video gốc (`D:/video goc may 2`) chiếm **232 GB** $\rightarrow$ Tổng dung lượng chạm trần 931 GB.
- Ổ `D:` Admin rơi vào trạng thái **0.00 MB Free**, khiến:
  1. Downloader crash: `[Errno 28] No space left on device: 'D:\video goc may 2\350\channel_info.json'`.
  2. Render chain crash: `System.IO.IOException` (Tee-Object / OutFileCommand fail khi PowerShell ghi log hoặc FFmpeg ghi output).

### Quy tắc Dọn dẹp & Giải phóng Đĩa Admin Chuẩn Farm:
- **Nguyên lý an toàn Farm**: Điện thoại trên farm chỉ lấy video từ thư mục render (`TIKTOK-videonuoinick-admin`) để upload lên TikTok, **hoàn toàn không đụng đến kho video gốc `video goc may 2`**.
- **Quy trình giải phóng dung lượng (~150 - 180 GB)**:
  1. Quét danh sách các folder trong `TIKTOK-videonuoinick-admin` đã có đầy đủ video render ($\ge 40$ clip).
  2. Với những folder đã render xong thành phẩm, tiến hành dọn dẹp các file `.mp4` trong `D:/video goc may 2/<folder>` tương ứng, chỉ giữ lại `avatar.jpg` và `channel_info.json`.
  3. Tuyệt đối không xóa các file cài đặt hệ thống hoặc thư mục render thành phẩm của bot.
- Sau khi giải phóng dung lượng về mức an toàn (> 100 GB trống), tiến trình cào sạch `run_admin_clean_vn_downloader.py` và chuỗi render `admin_render_chain.py` mới có thể tiếp tục vận hành bình thường.

---

## 6. Bẫy Downloader Tải Dư Thừa Gây Tái Tràn Đĩa (Redundant Download Prevention)

### Bẫy nhận định sai số lượng folder cần tải:
- Khi kiểm tra đĩa gốc `D:/video goc may 2`, nếu chỉ đếm folder có $\ge 30$ clip raw, script sẽ tưởng nhầm 514 folder đã dọn rác là "đang thiếu file" và cắm đầu tải lại $\rightarrow$ đĩa lại tràn về 0 MB trong vòng 20 phút.
- **Quy tắc kiểm tra đối soát 2 chiều bắt buộc**:
  ```python
  # raw_f -> render_f mapping:
  render_f = (m - 201) * 8 + slot
  
  # Chỉ tải nếu CẢ 2 NƠI ĐỀU THIẾU:
  render_count = len(glob("D:/TIKTOK-videonuoinick-admin/{render_f}/*.mp4"))
  raw_count = len(glob("D:/video goc may 2/{raw_f}/*.mp4"))
  
  if render_count >= 30:
      # ĐÃ XONG THÀNH PHẨM! Tuyệt đối không tải lại raw.
      skip()
  elif raw_count >= 30:
      # RAW ĐÃ ĐỦ, chỉ chờ render. Không tải thêm.
      skip()
  else:
      # Thực sự thiếu cả 2 -> Mới tải!
      download()
  ```

---

## 7. Quy trình Rà soát & Xử lý Trùng lặp Kênh / Video (Cross-Folder Collision Audit)

### Nguy cơ:
- Khi scraper rơi vào vòng lặp fallback không trỏ tiếp con trỏ (bug manifest rotation), một kênh (ví dụ: `Yêu Lu`) có thể bị tải nhân bản vào 5-10 folder khác nhau trên cùng máy hoặc đụng hàng sang máy khác.
- Dẫn đến tình trạng nhiều nick thuộc các Niche khác nhau (Marketing, Nhảy, Mỹ phẩm, Sự kiện) lại đăng chung 1 tập video giống hệt nhau từng byte.

### Phương pháp quét đối soát nhanh O(1) tránh lag:
1. **Quét Trùng Kênh & Claims:** So sánh `channel_info.json` và `gaixinh_channel_claims.json` giữa các folder.
2. **Quét Trùng File Video giữa các Folder:**
   - Lọc các file có dung lượng trùng nhau (`cand_sizes`).
   - Đọc 16KB đầu (`head = fp.read(16384)`) băm MD5 để tìm các cặp folder trùng 100% video.
3. **Quy trình xử lý khi phát hiện trùng:**
   - Xóa sạch video raw trùng lặp trong các folder bị nhân bản.
   - Tra cứu Niche thực tế của từng máy trong `Tik*.xlsx`.
   - Cấp kênh nguồn mới độc quyền 1:1 theo đúng Niche (creator cá nhân VN, Douyin visual thuần nhạc, ASMR không tiếng).
   - Cập nhật sổ cái Claims để khóa vĩnh viễn URL kênh, cấm tái sử dụng.

---

## 8. Bẫy Lỗi Luồng Video (Audio-Only Stream Trap & FFmpeg Render Crash)

### Hiện tượng:
- Khi chạy `random_batch_render.py` hoặc batch render, tiến trình đột ngột crash với exit code lạ `ffmpeg rc=4294967274` (thường ở một video cụ thể, ví dụ `15.mp4 -> 33.mp4`).

### Nguyên nhân gốc rễ:
- Video tải từ TikTok (qua yt-dlp) đôi khi là clip dạng slideshow ảnh hoặc bài đăng âm thanh, khiến file tải về chỉ có luồng âm thanh (`audio`), hoàn toàn KHÔNG CÓ luồng hình ảnh (`video stream`).
- Bộ lọc `filter_complex` trong FFmpeg (với các lệnh `trim`, `setpts`, scale) khi không tìm thấy stream `0:v` sẽ crash ngay lập tức.

### Giải pháp phòng ngừa & Xử lý:
1. **Kiểm tra luồng video ngay khi tải**:
   ```bash
   ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "<file.mp4>"
   ```
   Nếu output rỗng -> File không có luồng video. Bắt buộc xóa bỏ ngay và tải bù video khác.
2. **Quy tắc Swap Single Folder (Canonical Script: `D:/Taadaa/Tiktok-video/scripts/swap_single_folder_pipeline.py`)**:
   - Khi hoán đổi nguồn cho 1 folder/nick:
     * **Dọn sạch cả 2 đầu (Bắt buộc theo lệnh User: "phải dọn luôn video render r render lại khi folder nguồn mới")**: Cờ `--clean-old` xóa 100% video cũ trong cả `D:/video goc/<raw>` VÀ `D:/TIKTOK-videonuoinick/<render>` (hoặc `TIKTOK-videonuoinick-admin`). Tuyệt đối không giữ lại video render cũ, tránh bot upload đăng lẫn lộn giữa niche cũ và niche mới trên cùng một nick.
     * Tải đủ >= 40 clip có video stream hợp lệ (kiểm tra ffprobe `v:0`, loại bỏ file audio-only).
     * Tạo `avatar.jpg` (nếu `_make_avatar.py` không nhận diện được mặt người thì dùng FFmpeg fallback tại giây thứ 2 crop 512x512).
     * Bắt buộc render bắt đầu từ `start-seq = Video_Đã_Đăng + 1` (truyền `--start-seq`) để nối tiếp chính xác với số lượng video nick đã đăng trước đó.
     * Cập nhật đồng bộ 3 nơi: `Tik{args.tik}.xlsx` (lưu ý không hardcode Tik1.xlsx), SQLite `state.db` và sổ cái `claims.json`.
   - **Lệnh mẫu chuẩn**:
     ```bash
     python D:/Taadaa/Tiktok-video/scripts/swap_single_folder_pipeline.py \
       --folder-raw 143 --folder-render 498 --machine 63 --tik 2 \
       --channel "https://www.tiktok.com/@girlxinhdouyinn" --uploader "girlxinhdouyinn" \
       --niche-slug "gaixinh" --niche-label "Gái xinh" \
       --hashtag-pool "#gaixinh #douyin #trend #fyp #viral #xuhuong" \
       --min-videos 40 --start-seq 14 --clean-old
     ```
   - **Xử lý batch hoán đổi nhiều folder**: Dùng wrapper `D:/Taadaa/Tiktok-video/scripts/run_swap_kibe_duplicates.py` gọi tuần tự từng job, có đo thời gian và log nghiệm thu từng folder.

---

## 9. Định nghĩa Chuẩn "Niche Hot View" Nuôi Farm (Tránh Bẫy Hiểu Lệch Của Agent)

### 3 Điều kiện Tiên quyết:
1. **Cốt lõi:** KHÔNG CÓ TIẾNG NÓI NƯỚC NGOÀI (Cấm voiceover / lời thoại tiếng Trung xì xồ hoặc tiếng Anh lảm nhảm gây lộ nick clone).
2. **Kênh vừa tầm, không viral quá mức:**
   - CẤM lấy các idol triệu follow nổi tiếng toàn quốc (như Ngọc Kem, Lê Bống) vì mặt quá quen, thuật toán và người xem dễ nhận diện reup, dễ ăn gậy bản quyền.
   - Ưu tiên creator cá nhân vừa và nhỏ, phong cách đời thường mộc mạc, tự nhiên.
3. **Giữ chân người xem cao (Retention & FYP Optimization):**
   - **Gái xinh Douyin:** Thuần visual biến hình, nhảy trend theo nhạc nền bắt tai (BGM), không có thoại.
   - **Oddly Satisfying & ASMR:** Cắt xà phòng, cắt cát động lực, ép đồ vật $\rightarrow$ 100% âm thanh vật lý thư giãn, không tiếng người.
   - **Gái xinh nhảy trend Việt Nam:** Nhạc trend TikTok Việt, clip 10s - 35s.
   - **Thú cưng / Chó mèo hài hước:** Visual cute, không rào cản ngôn ngữ.

## 10. Tối ưu Đa luồng Render trên Farm Admin (Parallel Worker Scaling)

### Bối cảnh & Cấu hình phần cứng Admin:
- Máy Admin trang bị CPU mạnh: **28 Cores vật lý / 56 Cores logic (Threads)** cùng **64 GB RAM** (thường rảnh > 35 GB).
- Chạy render đơn luồng (`Parallel = 1`) gây lãng phí tài nguyên CPU (chỉ dùng ~35% CPU) và kéo dài thời gian hoàn thành 126 folder còn lại.

### Nâng cấp Supervisor `admin_render_chain.py` hỗ trợ `--parallel`:
- Thêm tham số `--parallel` vào `build_arg_parser()` (mặc định = 2):
  ```python
  parser.add_argument(
      "--parallel",
      type=int,
      default=2,
      help="Parallel FFmpeg render workers (default: 2)",
  )
  ```
- Hàm `run_step(step_num, script_path, parallel=args.parallel)` tự động truyền `-Parallel <N>` xuống kịch bản PowerShell của từng bước:
  ```python
  cmd = [
      "powershell.exe",
      "-NoProfile",
      "-ExecutionPolicy",
      "Bypass",
      "-File",
      str(script_path),
      "-StartMachine",
      "201",
      "-EndMachine",
      "280",
      "-Parallel",
      str(parallel),
      "-AutoRun",
  ]
  ```

### Hiệu quả kiểm chứng thực tế (`--parallel 2`):
- Khi chạy `--parallel 2`, script kích hoạt đồng thời **2 tiến trình FFmpeg song song** trên 2 video khác nhau.
- **Tải phần cứng:** CPU đạt mức tối ưu vàng **~70 - 75%**, RAM chiếm ~42% (hoàn toàn an toàn, không giật lag hệ thống).
- **Tốc độ:** Tăng gấp đôi ($\times 2$), rút ngắn 50% thời gian render toàn bộ các dàn Tik6 $\rightarrow$ Tik8.

### Lệnh khởi chạy Supervisor Admin chuẩn với Worker = 2:
```bash
ssh admin-farm 'python D:/Taadaa/Tiktok-video/scripts/admin_render_chain.py --skip-wait-tik2 --start-from 6 --parallel 2'
```

---

## 11. Bẫy Ngắt Kết Nối SSH Cho Tiến Trình Render Dài Hạn (SSH Detached Process Invariant)

### Triệu chứng & Rủi ro:
- Khi chạy chuỗi batch render hoặc supervisor script (`admin_render_chain.py`) trên máy Admin từ xa qua SSH:
  * Nếu phiên terminal SSH foreground bị ngắt kết nối, rớt mạng LAN/Wi-Fi hoặc chạm trần timeout phiên làm việc của agent (ví dụ trần 6 giờ / 21.600s), OpenSSH daemon trên Windows sẽ tự động gửi tín hiệu kết thúc (SIGHUP / SIGTERM, thể hiện bằng `exit code 1` hoặc `exit code 15`) đến tiến trình con.
  * Hậu quả: Tiến trình render bị dừng đột ngột giữa chừng (ví dụ đang render máy 267 thì đứt), khiến chuỗi render bị bỏ dở.

### Giải pháp Bất biến Vận hành (Windows OpenSSH Detached Execution):
1. **Tuyệt đối không neo tiến trình render dài hạn (> 30 phút) vào session SSH foreground**.
2. **Khởi chạy độc lập hoàn toàn bằng PowerShell `Start-Process` (Detached WindowStyle Hidden)**:
   ```bash
   ssh admin-farm 'powershell -Command "Start-Process -FilePath cmd.exe -ArgumentList \"/c D:\Taadaa\Tiktok-video\run_admin_render_chain.bat\" -WindowStyle Hidden"'
   ```
3. **Cấu hình launcher chuẩn hóa (`D:/Taadaa/Tiktok-video/run_admin_render_chain.bat`)**:
   Luôn thiết lập mặc định `--parallel 2` trong file `.bat`:
   ```bat
   @echo off
   setlocal
   set PYTHONUTF8=1
   set PYTHONIOENCODING=utf-8
   set TIKTOK_VIDEO_RUNTIME_ROOT=D:\CodexRuntime\tiktok-video
   set PATH=C:\Users\Admin\AppData\Local\hermes\hermes-agent\venv\Scripts;%PATH%
   cd /d D:\Taadaa\Tiktok-video
   "C:\Users\Admin\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" -u scripts\admin_render_chain.py --skip-wait-tik2 --start-from 8 --parallel 2 > "D:\CodexRuntime\tiktok-video\batch-runs\admin_render_chain.stdout.log" 2>&1
   ```
4. **Giám sát không xâm nhập (Non-intrusive Polling)**:
   Sau khi kích hoạt detached process, kiểm tra tiến độ qua log file (`admin_render_chain.stdout.log`) hoặc danh sách tiến trình `psutil` (kiểm tra `ffmpeg.exe` và `python.exe`), tuyệt đối không spawn lại lệnh render mới khi tiến trình cũ đang chạy để tránh xung đột file khóa hoặc tranh chấp tài nguyên.






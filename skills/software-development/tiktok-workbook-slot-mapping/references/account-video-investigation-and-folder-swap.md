# Điều tra nguồn video tài khoản & Quy trình đổi nguồn video (Video Folder Swap)

## 1. Khi nào kích hoạt quy trình
- Khi phát hiện một nick TikTok trên Farm đăng nội dung nhạy cảm, vi phạm chính sách, sai chủ đề (ví dụ: kênh chính trị, lịch sử nhạy cảm VNCH/chiến tranh, reup kênh vi phạm bản quyền hoặc sai niche).
- Khi người dùng yêu cầu: "Kiểm tra nick này làm video gì", "Vào xem folder video của nó", "Đổi nguồn video nick này".
- Khi chuyển đổi hàng loạt tài khoản ít/chưa đăng video (0 clip) sang niche mới (ví dụ chuyển đổi 27 máy 0 video của Tik7 sang kênh Gái Xinh visual).

---

## 2. Quy trình định vị O(1) từ Nick ra Thư mục video

### Bước 1: Tra cứu máy và slot từ SQLite
```python
import sqlite3
conn = sqlite3.connect("D:/Taadaa/data/tiktok_tracker.db")
c = conn.cursor()
c.execute("SELECT username, may, tik, host_id FROM farm_account_info WHERE username = ?", (username,))
res = c.fetchone()
print(res) # e.g. ('bmwarclxp1f', 52, 5, 'kibe')
```
* **Kết quả**: Xác định được `may` (Máy 52), `tik` (Slot Tik5), và `host_id` (`kibe` hoặc `admin`).

### Bước 2: Đọc thông tin mapping trên file Workbook Tik tương ứng
File Excel nằm tại: `D:/OneDrive/TaadaaData/{host_id}/Tik{tik}.xlsx`
* **Dòng `may`**:
  - Cột A (0): `Máy` (ví dụ: 52)
  - Cột B (1): `device ID` (Serial ADB)
  - Cột C (2): `ID` (Username TikTok)
  - Cột D (3): `Folder Video` (Thư mục render để bot upload: `D:/TIKTOK-videonuoinick/{Folder Video}/`)
  - Cột E (4): `video gốc` (Thư mục video gốc tải về: `D:/video goc/{video gốc}/`)
  - Cột F (5): `Keyword Video` (Niche/từ khóa video)
  - Cột G (6): `Hashtag Pool` (Bộ hashtag gán khi đăng)
  - Cột H (7): `Video Đã Đăng` (Số lượng video bot đã đăng lên kênh)

---

## 3. Quy trình kiểm tra nội dung video nhanh (O(1) Inspection)
* **Tuyệt đối cấm** quét đĩa diện rộng (`os.walk`, `glob(recursive=True)`).
* Trích xuất frame đại diện của video bằng `ffmpeg` và đọc nội dung bằng Windows OCR:
```bash
# Trích xuất 1 frame tại giây thứ 3
ffmpeg -y -ss 00:00:03 -i "D:/TIKTOK-videonuoinick/{Folder Video}/4.mp4" -vframes 1 -q:v 2 "C:/Users/Kibe/video_sample.jpg"

# Nhận diện chữ/tiêu đề trên video qua Windows native OCR (BẮT BUỘC dùng backslash path)
powershell -ExecutionPolicy Bypass -File C:/Users/Kibe/simple_ocr.ps1 "C:\Users\Kibe\video_sample.jpg"
```
* **Lưu ý PowerShell OCR**: `C:/Users/Kibe/simple_ocr.ps1` dùng WinRT API `StorageFile.GetFileFromPathAsync`, bắt buộc đường dẫn dạng Windows backslash (`C:\Users\Kibe\...`), nếu truyền slash `/` sẽ bị lỗi AggregateException.
* **Lưu ý cô lập PYTHONPATH khi chạy script/test trên Windows**: Khi chạy python trong venv automation từ terminal agent, biến môi trường `PYTHONPATH` có thể bị dính các thư viện của Hermes venv gây xung đột C-extension (ví dụ lỗi NumPy `No module named 'numpy._core._multiarray_umath'`). Bắt buộc dùng `env -u PYTHONPATH python <script>.py` để cô lập hoàn toàn môi trường.

---

## 4. Quy trình đổi nguồn video (Folder Swap Protocol)

1. **Dọn dẹp triệt để cả hai đầu (`--clean-old`)**:
   - Khi gán kênh mới, bắt buộc dọn sạch cả 2 thư mục:
     1. Video gốc cũ: `D:/video goc/{folder}/*`
     2. Video render cũ: `D:/TIKTOK-videonuoinick/{folder}/*`
   - Tuyệt đối không để lẫn video cũ của niche khác vào thư mục render mới.
2. **Quy tắc phân bổ 2 tầng (Exclusive vs Curated Hub), Quota 40-45 & Chống trùng nguồn**:
   - **Chỉ tiêu chuẩn hóa**: Min 40 video (`--min-videos 40`), Max 45 video (`--max-videos 45`) cho mỗi folder.
   - **Kênh Độc Quyền (Exclusive - Kênh đủ >= 40 clip)**: 
     - Lấy tối đa 45 video đầu (`vids[:max_videos]`) cho folder độc quyền.
     - **Gom video thừa (Leftover Pool Recycling)**: Toàn bộ video từ video thứ 46 trở đi (`vids[max_videos:]`) tự động đẩy vào Bể Gộp đa kênh (`curated_channels`) để chia đều cho các kênh tổng hợp, tránh lãng phí video đẹp và không trùng lặp.
   - **Kênh thiếu < 40 clip**: Nạp vào Bể Gộp (`curated`), phân bổ đều từ **tất cả** các kênh thiếu với tỉ lệ random, xáo trộn thứ tự.
   - **Cơ chế chống trùng nguồn toàn Farm (Cross-Folder Channel Deduplication)**:
     - Sổ cái đăng ký kênh tập trung: `D:/Taadaa/Tiktok-video/data/gaixinh_channel_claims.json`.
     - File metadata tại từng folder: `D:/video goc/<folder>/channel_info.json`.
     - Kênh nguồn một khi đã cấp cho 1 folder thì các folder khác tự động `[SKIP CLAIMED]`. Khi truyền flag `--clean-old`, hệ thống tự động nhả claim cũ của folder.
   - **Cấm bắt User soi link / duyệt video thủ công**: Phải chạy qua AI Vision ViT ONNX (`ai_channel_filter.py`) tự động kiểm duyệt frame tại giây thứ 2 và thứ 5.
3. **Cấu hình tải & render an toàn cho Farm**:
   - **Tải video**: Dùng 20 workers đa luồng (`--parallel 20`) qua Proxy Pool (`proxy_pool_67.txt`). Lưu ý URL-encode password proxy chứa ký tự `#` (`%23`) để yt-dlp parse đúng.
   - **Render video**: Dùng đúng **1 worker FFmpeg (`--parallel 1`)** tuần tự để tiết kiệm CPU/GPU máy chủ (`scripts/run_render_5_folders.py`).
4. **Quy tắc bảo toàn 'Video Đã Đăng' & Đánh số Video Render Mới (BẮT BUỘC THEO USER)**:
   - **TUYỆT ĐỐI CẤM reset cột H (`Video Đã Đăng`) về 0** nếu nick đã đăng clip (tránh bot upload nhặt trùng số cũ hoặc làm lệch lịch sử nick).
   - **Giữ nguyên giá trị `Video Đã Đăng`** (ví dụ nick đã đăng 3 video thì giữ nguyên 3).
   - **Đánh số video render mới bắt đầu từ clip tiếp theo**: Truyền cờ `--start-seq <Video_Đã_Đăng + 1>` vào `random_batch_render.py` (ví dụ nick đã đăng 3 thì render mới bắt đầu từ `4.mp4`, `5.mp4`, ...). Bot upload sẽ tự động nhặt `4.mp4` chạy tiếp trơn tru.
   - **Cập nhật Workbook `Tik{N}.xlsx`**:
     - Cột E (`video gốc`): Điền số folder nguồn mới (nếu đổi folder gốc).
     - Cột F (`Keyword Video`): Cập nhật từ khóa mới (ví dụ: `Gái xinh`).
     - Cột G (`Hashtag Pool`): Cập nhật bộ hashtag chuẩn theo niche mới.
     - Cột H (`Video Đã Đăng`): GIỮ NGUYÊN giá trị hiện tại.
5. **Khắc phục lỗi mất thumbnail HEVC trên Windows Explorer**:
   - Cài `Microsoft.HEVCVideoExtension` qua PowerShell `Add-AppxPackage` và restart Explorer để hiện preview ảnh đại diện cho các video 1080p H.265.

---

## 5. Pipeline thực thi Swap tự động khép kín (Automated Single Folder Swap Pipeline)

Để tránh thao tác thủ công nhiều bước dễ sai sót hoặc lệch cursor, toàn bộ quy trình swap nguồn video cho một tài khoản đã được chuẩn hóa vào script:
`D:/Taadaa/Tiktok-video/scripts/swap_single_folder_pipeline.py`

### Cú pháp CLI chuẩn:
```bash
python D:/Taadaa/Tiktok-video/scripts/swap_single_folder_pipeline.py \
  --folder-raw <folder_goc> \
  --folder-render <folder_video_render> \
  --machine <so_may> \
  --tik <so_tik> \
  --channel "<url_kenh>" \
  --uploader "<ten_kenh>" \
  --niche-slug "<slug>" \
  --niche-label "<label>" \
  --min-videos 40 \
  --start-seq <Video_Đã_Đăng + 1> \
  --clean-old
```

### 5 Bất biến bắt buộc trong Pipeline:
1. **Dọn sạch cả 2 đầu (`--clean-old`)**: Xóa sạch toàn bộ video cũ trong `D:/video goc/<folder_raw>` và `D:/TIKTOK-videonuoinick/<folder_render>` trước khi tải.
2. **Tải qua Proxy MikroTik LAN**: Xoay ngẫu nhiên các cổng `10001..10035` (`192.168.110.2`) để chống rate-limit từ TikTok/YouTube.
3. **Tạo Avatar chuẩn (`_make_avatar.py`)**: BẮT BUỘC truyền cờ `--source-root "D:/video goc"` và inject `PYTHONPATH` trỏ về `scripts/` để không bị nhảy nhầm sang ổ fallback `D:/video goc may 2`.
4. **Bảo toàn lịch sử đăng & Đánh số Render Mới (`--start-seq`)**: 
   - Đọc cột `Video Đã Đăng` từ workbook (ví dụ đã đăng 26 clip).
   - Truyền `--start-seq 27` vào `random_batch_render.py` để render ra `27.mp4`, `28.mp4`... Bot upload sẽ tự động nhặt clip tiếp theo mà không bị trùng lặp hay lùi cursor.
5. **Đồng bộ nguyên tử 3 điểm**:
   - **Excel (`TikN.xlsx`)**: Cập nhật cả 2 sheet (`TaiKhoan` và `Hashtag theo Folder`), giữ nguyên `Video Đã Đăng`, cập nhật `Keyword Video`, `Hashtag Pool`, `Số Video = len(downloaded)` và `Kiểm Tra = OK`.
   - **SQLite (`state.db`)**: Update bảng `folders` (`status = 'complete'`, `video_count`, `niche`, `source_channel`, `uploader`) và xóa/chèn mới vào bảng `videos`.
   - **Sổ cái Claim (`gaixinh_channel_claims.json`)**: Khóa kênh mới cho folder mục tiêu để các folder khác tự động `[SKIP CLAIMED]`.
6. **Frame nghiệm thu**: Tự động trích xuất frame tại giây thứ 2 của `start_seq.mp4` ra file ảnh kiểm chứng để phục vụ nghiệm thu thị giác.

---

## 6. Xử lý sự cố ACCOUNT_SWITCHER_FAILED / ACCOUNT_VERIFY_MISMATCH khi Up Video / Avatar
- **Triệu chứng**:
  Khi chạy `run_tiktok_upload_batch.ps1` (hoặc `-AvatarOnly`), runner exit với mã lỗi:
  ```
  [ACCOUNT_SWITCHER_FAILED] ACCOUNT_READY verify failed: ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account. Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa, dismiss popup/onboarding thủ công rồi retry.
  [EDGE] CAPTCHA detected during account switch
  ```
- **Bẫy cảnh báo sai (`[EDGE] CAPTCHA detected`)**:
  Đây là fallback của state machine sau khi retry kiểm tra profile 3 lần không khớp username; **hoàn toàn KHÔNG PHẢI do bị dính Captcha thật**.
- **Nguyên nhân gốc rễ**:
  Tài khoản mục tiêu (ví dụ `@bmwarclxp1f`) **chưa đăng nhập hoặc bị văng session** khỏi ứng dụng TikTok trên máy. Danh sách Account Switcher chỉ có 7 tài khoản khác, thiếu mất tài khoản cần xử lý. Tool không tìm thấy username trong switcher nên profile vẫn giữ nguyên tài khoản cũ.
- **Quy trình xử lý chuẩn Farm**:
  1. **Kiểm tra Account Switcher**: Dùng ATX JSON-RPC hoặc ADB chụp ảnh / dump hierarchy menu Switcher để xác định chính xác danh sách nick đang đăng nhập trên thiết bị.
  2. **Tra cứu Credentials**: Tìm kiếm username trong file Source of Truth `taikhoan_dat_v2_updated .xlsx` (hoặc DB `farm_account_info`) để lấy:
     - TikTok ID & Password
     - 2FA Secret Key (TOTP 32 ký tự)
     - Email khôi phục (Hotmail / Gmail)
  3. **Thực thi Login Bù**:
     - Tuân thủ nghiêm ngặt Invariant Farm: *"Thiếu nick switcher -> Tự chạy script login bù ngay (dùng flow ID + Pass + TOTP), sau đó mới thực hiện tiếp tác vụ upload video / avatar"*.
     - Tuyệt đối cấm xóa tài khoản khác hoặc làm lệch mapping giữa Excel và DB.

---

## 7. Bẫy giao diện TikTok 47.x khi đổi Avatar & Nhận diện Nút Bút Chì góc trên bên trái
- **Bẫy bấm vào Vòng Tròn Avatar (`Ảnh hồ sơ` / bounds `[708,300][1080,636]` / center `(894, 468)` / `(540, 336)`)**:
  - Trên TikTok phiên bản mới (47.x), bấm vào vòng tròn avatar hoặc icon dấu cộng nhỏ ở góc dưới avatar sẽ mở ra màn hình **"Thêm vào Nhật ký" (Story Camera / Story Media Picker)** thay vì mở màn "Sửa hồ sơ".
  - State machine sẽ bị kẹt hoặc báo `SKIPPED_AVATAR_EDIT_UNAVAILABLE: TikTok báo hoạt động sửa avatar không có sẵn trên profile phụ`.
- **Giải pháp chuẩn xác (Top-Left Pencil Button)**:
  - Trên header Profile TikTok 47.x (độ phân giải 1080x1920 trên máy Samsung S7), nút mở "Sửa hồ sơ" chính là **Icon Bút Chì nằm ở góc trên bên trái**:
    - Bounds XML: `[24,96][126,204]` (hoặc tọa độ center khoảng `(75, 150)`).
    - Class: `android.widget.ImageView` (thường nằm cạnh nút QR code).
  - Tapping vào tọa độ này (`75, 150`) sẽ mở trực tiếp màn hình `Sửa hồ sơ` chứa nút `Thay đổi ảnh` (`[396,552][683,609]`).
  - Trong `state_machine.py`: Bắt buộc tích hợp `StateMachine._find_new_profile_pencil(xml_text)` ngay đầu hàm `_find_profile_edit_button` để ưu tiên tap icon bút chì này trước khi rơi xuống các fallback tap avatar circle.

---

## 8. Bẫy trích xuất Avatar từ Video (Cosplay / Anime / Frame nền tối)
- **Bẫy Frame nền tối / Chuyển cảnh (Black/Dark frame)**:
  - Nếu trích xuất ảnh frame tại giây cố định (ví dụ giây thứ 3) mà trúng cảnh mờ dần (fade out) hoặc background tối, Mean BGR của ảnh < 30 (gần như đen sì), avatar tải lên sẽ không thấy rõ người.
- **Bẫy Kênh Reup / Cosplay Anime (`#cosplayer #hoathinhtrungquoc`)**:
  - Một số kênh trong manifest gắn mác "Gái xinh" (ví dụ `@gaixinh.nhaydep`) nhưng thực chất là kênh tổng hợp reup lẫn lộn nhân vật **Cosplay Anime game** (tóc giả sặc sỡ, trang điểm đậm dạng búp bê/hoạt hình như nhân vật Genshin Impact), phim ngắn cổ trang và gym.
  - Khi crop cận cảnh khuôn mặt làm avatar, ảnh đại diện trông như ảnh anime/hoạt hình vẽ tay khiến user khó chịu vì sai chủ đề hotgirl đời thực.
- **Biện pháp phòng ngừa & Tiêu chuẩn chọn nguồn**:
  - Luôn kiểm tra metadata / hashtag video (`#cosplayer`, `#anime`, `#hoathinh` -> REJECT) trước khi gán kênh độc quyền.
  - Ưu tiên các kênh cá nhân hotgirl người thật 100% đời thường (`@vtkh2004`, `@lebong95`, `@thuy_tien_2000`).
  - Sử dụng thuật toán Haar Cascade / MediaPipe Face Detection quét qua các frame từ 1.0s đến 4.0s, chọn frame có **đúng 1 khuôn mặt người thật, độ sáng (brightness/value) đạt từ 100 đến 180**, crop tỷ lệ 1:1 bao quanh mặt (size = face_size * 2.0) để tạo avatar sáng đẹp, tự nhiên.

---

## 9. Quy chuẩn Niche Hot View Thuần VN (CỐT LÕI: KHÔNG CÓ TIẾNG NƯỚC NGOÀI)

### ⚠️ BẤT BIẾN TỐI CAO TỪ USER (HARD CONSTRAINTS):
1. **CỐT LÕI: TUYỆT ĐỐI KHÔNG ĐƯỢC CÓ TIẾNG NÓI NƯỚC NGOÀI (Cho phép Douyin visual & ASMR không tiếng)**:
   - **Bản chất yêu cầu của User**: User cho phép cào cả **Douyin gái xinh** và **ASMR không tiếng** thuộc chung nhóm "niche hot view thuần VN". CẤM agent hiểu cứng nhắc thành "chỉ được lấy kênh đăng ký tại VN" rồi tự ý loại bỏ Douyin hay ASMR.
   - **Tiêu chuẩn cấm tuyệt đối**: CẤM CÓ TIẾNG NÓI NGOẠI LAI (cấm tiếng người xì xồ tiếng Trung, cấm voiceover nói tiếng Anh hay ngôn ngữ khác linh tinh vào video).
   - **3 nhóm Niche Hot View được phép & ưu tiên cao**:
     * **Douyin Gái Xinh visual thuần nhạc / BGM**: Nhảy trend, biến hình, OOTD, phong cách cuốn hút, **KHÔNG CÓ LỜI THOẠI TIẾNG TRUNG** -> Giữ chân người xem cực tốt, cắn đề xuất mạnh tại thị trường VN.
     * **Oddly Satisfying & ASMR không tiếng**: Cắt xà phòng, cát động lực, ép đồ vật, âm thanh vật lý thư giãn -> **100% không tiếng người nói**, không rào cản ngôn ngữ, retention rate kịch trần.
     * **Kênh Creator cá nhân Việt Nam**: Nhạc trend TikTok Việt, quay đời thường tự nhiên, phù hợp tên nick.
2. **"NICHE NHIỀU VIEW" $\ne$ "KÊNH IDOL VIRAL TRIỆU FOLLOW"**:
   - **Sai lầm tai hại (Bị User mắng)**: Tìm ngách nhiều view lại đi tải video của các Idol/Hot girl triệu follow (Ngọc Kem, Lê Bống, Đào Lê Phương Hoa...). Mặt họ đã quá quen mặt trên TikTok VN, người xem nhìn vào biết ngay nick clone/reup giả mạo, dễ dính gậy bản quyền và bị thuật toán đánh spam/bóp reach nặng.
   - **Định nghĩa chuẩn của User**:
     - **Đúng Niche nhiều view**: Chọn các ngách có thuật toán ưu tiên giữ chân người xem (Retention & Loop rate cao) như: Gái xinh nhảy trend TikTok / đời thường VN, Douyin visual thuần nhạc, ASMR không tiếng, Thú cưng cute (chó mèo), Mẹo vặt / Ẩm thực đường phố VN.
     - **Kênh ÍT VIRAL HƠN**: Bắt buộc chọn các **kênh cá nhân, creator nhỏ hoặc vừa của Việt Nam** (ví dụ `@lelephomaiquee`, `@gi.xinh.y46`, `@hnh999995`...): clip quay tự nhiên, nhạc trend TikTok Việt Nam, mặt mộc mạc đời thường, chưa bị nhận diện rộng rãi. Khi reup và render lách thuật toán, nick trông y hệt một người dùng thật đang chia sẻ cuộc sống cá nhân, cắn đề xuất tự nhiên rất bền và an toàn.
3. **BẮT BUỘC DỌN SẠCH CẢ VIDEO RENDER CŨ KHI SWAP NGUỒN MỚI**:
   - **Chỉ thị trực tiếp từ User**: *"Thế thì phải dọn luôn video render r render lại khi folder nguồn mới chứ"*.
   - **Nguyên lý**: Khi hoán đổi nguồn cho folder, nếu không dọn sạch folder render cũ (`D:/TIKTOK-videonuoinick/<render>`), bot farm trên điện thoại sẽ tiếp tục bốc các video render cũ của niche cũ để đăng, hoặc làm trộn lẫn 2 chủ đề hoàn toàn khác nhau trên cùng 1 nick (ví dụ: đang đăng marketing tự nhiên nhảy sang gái xinh lẫn lộn).
   - **Bắt buộc**: Dọn sạch 100% file trong cả `D:/video goc/<raw>` VÀ `D:/TIKTOK-videonuoinick/<render>`, sau đó render mới toàn bộ từ `start_seq = Video_Đã_Đăng + 1`.

### Thứ tự ưu tiên các Niche nhiều view tại Việt Nam:
1. **Top 1: Gái xinh nhảy trend nhạc Việt & Đời thường (Creator vừa/nhỏ VN)**:
   - Các bạn nữ Việt Nam quay clip nhảy ngắn theo nhạc trend TikTok thịnh hành, biểu cảm tự nhiên, visual dễ nhìn.
   - Thời lượng dải vàng: **10s – 35s** (tối ưu 100% completion rate).
   - Tương thích tốt nhất với profile nữ Việt (như tên Khánh Linh, Thảo, Trang...).
2. **Top 2: Thú cưng Việt Nam (Chó mèo cute / hài hước đời thường)**:
   - Kênh thú cưng cá nhân người Việt chăm sóc chó mèo, tình huống hài hước đời thường.
   - Tỷ lệ chia sẻ (Share) và thả tim tự nhiên rất cao.
3. **Top 3: Ẩm thực đường phố & Món ngon Việt Nam (Street Food VN)**:
   - Cận cảnh nấu nướng, đồ ăn đường phố Việt Nam, màu sắc bắt mắt, âm thanh xèo xèo giòn rụm.

### Kỷ luật tự quyết định (Không hỏi thừa / Không lạm dụng clarify):
- Khi user chỉ đạo "Tự chọn đi" hoặc task đã rõ tiêu chí view cao: Bắt buộc chọn kênh cá nhân VN ít viral thuộc Top 1 hoặc Top 2, triển khai trọn gói dứt điểm, không hỏi vòng vo.

---

## 10. Pipeline chuẩn hóa thay thế nguồn video (`swap_single_folder_pipeline.py`)
- Script trung tâm: `D:/Taadaa/Tiktok-video/scripts/swap_single_folder_pipeline.py`
- Lệnh chạy chuẩn:
  ```bash
  python D:/Taadaa/Tiktok-video/scripts/swap_single_folder_pipeline.py \
    --folder-raw <folder_goc> \
    --folder-render <folder_video_render> \
    --machine <so_may> \
    --tik <so_tik> \
    --channel "<url_kenh>" \
    --uploader "<ten_kenh>" \
    --niche-slug "<slug>" \
    --niche-label "<label>" \
    --hashtag-pool "<hashtags>" \
    --min-videos 40 \
    --start-seq <Video_Đã_Đăng + 1> \
    --clean-old
  ```
- **Các điểm cốt lõi đã tích hợp trong pipeline**:
  1. Dọn sạch 2 đầu (`clean_directory`) cả kho raw và kho render.
  2. Tải qua proxy MikroTik LAN `10001..10035` (`192.168.110.2`) với dải thời lượng chuẩn `10s - 75s`.
  3. Tự động gọi `_make_avatar.py` với `--source-root "D:/video goc"` và inject `PYTHONPATH` nội bộ.
  4. Đánh số render nối tiếp bắt đầu từ `Video_Đã_Đăng + 1` để giữ nguyên lịch sử cột H trong Excel, bot upload nhặt tiếp video mới tinh không trùng lặp.
  5. Cập nhật đồng bộ cả 2 sheet trong `TikN.xlsx`, ghi nhận vào SQLite `state.db` và sổ cái `gaixinh_channel_claims.json`.
  6. Tự động xuất frame kiểm chứng nghiệm thu tại giây thứ 2 để gửi ảnh MEDIA: cho user.

---

## 11. Bẫy file video tải về không có luồng hình ảnh (Audio-only / Missing Video Stream Pitfall)
- **Hiện tượng**:
  Khi chạy `random_batch_render.py`, một tác vụ render bất ngờ crash với lỗi:
  ```text
  failed: 15.mp4 -> 33.mp4 (ffmpeg rc=4294967274)
  ```
- **Nguyên nhân gốc rễ**:
  Khi `yt-dlp` tải clip từ TikTok hoặc YouTube Shorts (đặc biệt khi fallback hoặc dính format âm thanh riêng lẻ), file tải về mang đuôi `.mp4` nhưng thực chất chỉ chứa luồng âm thanh (`codec_name: mp3` hoặc `aac`), hoàn toàn không có luồng hình ảnh (`video stream = None`).
  Khi script render áp chuỗi video filter (`scale`, `crop`, `pad`), FFmpeg không tìm thấy luồng video đầu vào và crash ngay lập tức.
- **Biện pháp phòng ngừa & Kiểm tra Pre-flight**:
  Trước khi bắt đầu render batch, bắt buộc quét kiểm tra toàn bộ file trong folder video gốc bằng `ffprobe`:
  ```python
  import subprocess, json

  def check_valid_video_stream(file_path: str) -> bool:
      cmd = ['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'json', file_path]
      res = json.loads(subprocess.check_output(cmd, text=True))
      streams = res.get('streams', [])
      return any(s.get('codec_type') == 'video' for s in streams)
  ```
  Nếu phát hiện file chỉ có audio (`not check_valid_video_stream`): Lập tức xóa file lỗi đó và tải bù 1 video khác từ kênh trước khi khởi chạy render.



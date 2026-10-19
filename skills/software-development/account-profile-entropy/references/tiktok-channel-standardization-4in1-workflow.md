# Quy Chuẩn Chuẩn Hoá Kênh TikTok Toàn Diện 4 Món (Avatar - Hashtag - Bài Pin - Bio)

## 1. Định Nghĩa & Lệnh Của Operator (User Directive 2026-10-18)
- **Chỉ thị của Operator**: *"Từ h nói chuẩn hoá là ngoài ava hashtag bài pin thì chuẩn hoá luôn bio"*
- Trước đây, quy trình chuẩn hoá kênh chỉ gồm 3 món (Avatar - Hashtag - Ghim video).
- **Từ nay, khi Operator yêu cầu "Chuẩn hoá kênh này" / "Chuẩn hoá acc này"**: BẮT BUỘC thực thi đầy đủ **bộ 4 món**:
  1. **Avatar (Ảnh đại diện)**
  2. **Hashtag & Niche**
  3. **Bài pin (Pin Top Video $\ge 1.000$ views)**
  4. **Bio (Tiểu sử có dấu chuẩn tiếng Việt)**

## 2. Quy Trình 4 Bước Chuẩn Hoá Chi Tiết

### Bước 1: Tra cứu tọa độ Farm $O(1)$ từ Username / Ảnh Profile
- Nhận diện `@username` từ ảnh chụp profile.
- Truy vấn SQLite `D:/Taadaa/data/tiktok_tracker.db`:
  - `farm_account_info`: Xác định `may`, `tik`, `host_id` (kibe: máy 1–80, admin: máy 201+).
  - `snapshots`: Kiểm tra UID, follower, heart, video count, view count của các clip.
- Đối soát `Tik<N>.xlsx` và `taikhoan_dat_v2_updated .xlsx` trong `D:/OneDrive/TaadaaData/<cluster>/`:
  - Xác định `Folder Video` ($F_{vid}$ - kho render) và `Video Goc` ($F_{src}$ - kho nguồn).
  - Lấy `Keyword Video` và `Hashtag Pool` tương ứng.

### Bước 2: Món 1 — Ghim Video (Pin Gate $\ge 1.000$ views)
- Tiêu chuẩn farm: **Chỉ ghim video khi có clip đạt $\ge 1.000$ views**.
- Nếu clip có view cao nhất $< 1.000$ views: Giữ nguyên thứ tự tự nhiên của lưới video, không ghim.
- Nếu có $\ge 1$ clip $\ge 1.000$ views:
  - Dùng canonical tool `python D:/Taadaa/tools/pin_top_videos.py --machine <May> --account <username>`.
  - Nếu đã đủ 3 bài ghim, tool tự động swap bài view cao hơn thay thế bài pin view thấp nhất.

### Bước 3: Món 2 — Hashtag & Niche (Khắc Phục Tận Gốc Lỗi Bị Lộn Ngược Sau 15 Phút)
- **Bẫy Niche Desync giữa Sổ Cái và Video Thực Tế**: Cột `Keyword Video` trong `Tik<N>.xlsx` thường bị lưu vết cũ hoặc generic (VD: `Thú vị`, `Nhảy` nhưng video thực tế là Gym hoặc Phim ngắn học đường). BẮT BUỘC đối soát trực tiếp hình ảnh clip trên grid Profile của kênh trước khi chốt ngách; TUYỆT ĐỐI CẤM tin mù quáng vào cột Keyword trong Excel.
- **Gốc Rễ Lỗi Hashtag Cứ Bị Lộn Hoài (User Phản Ứng: 'tại sao hashtag cứ bị lộn hoài bực quá đi')**:
  * Hệ thống có tiến trình cron ngầm chạy mỗi 15 phút (`sync_all_tik_keywords.py`) để đồng bộ Niche và Hashtag từ CSDL video trung tâm (bảng `folders`) vào các file Excel `Tik*.xlsx`.
  * Nếu Coordinator chỉ mở file Excel ra sửa (sửa ngọn), thì chỉ sau 15 phút, con cron này lại đọc CSDL nguồn trung tâm và **TỰ ĐỘNG GHI ĐÈ LẠI** nhãn cũ vào Excel!
  * **Quy tắc sửa dứt điểm 3 bước**:
    1. Cập nhật CSDL video nguồn trung tâm trước (sửa cột `niche` của folder nguồn $F_{src}$ và folder render $F_{vid}$).
    2. Cập nhật đồng bộ cả 2 file Excel (`kibe/Tik<N>.xlsx` VÀ `admin/Tik<N>.xlsx`).
    3. Cắm cờ khóa cứng `.manual_hashtag_locked` trong cả 2 thư mục (kho nguồn $F_{src}$ và kho render $F_{vid}$).
- Đối soát nội dung clip thực tế trên kênh để cập nhật đúng ngách và pool hashtag chuẩn:
  - Cắm marker `.manual_hashtag_locked` trong thư mục video render $F_{vid}$ (`D:/TIKTOK-videonuoinick/<F>/` hoặc `D:/TIKTOK-videonuoinick-admin/<F>/`).
  - Ghi nhận vào `manual_hashtag_protected_folders.json`.

### Bước 4: Món 3 — Avatar Bám Lưới & Cận Cảnh Ngũ Quan
- Trích xuất 2 phương án từ video kho nguồn $F_{src}$ / kho render $F_{vid}$:
  - Chuẩn kích thước: Vuông $512 \times 512$.
  - **Kỹ thuật trích xuất & Fallback khi Haar Cascade miss (0 face)**: Với các video tiểu phẩm/kịch hoặc hoạt hình/học đường, Haar Cascade thường trả về 0 face $\rightarrow$ BẮT BUỘC fallback sang trích xuất khung hình theo mốc thời gian (`dump_sample_frames` tại giây 2, 5, 8, 12) rồi crop tâm chủ thể (`crop_head_square`), không để quy trình bị treo.
  - Cung cấp ảnh đối sánh gồm cả ảnh vuông và mô phỏng viền tròn Profile (`make_circle_preview` với viền xanh lá).
  - **Ghép Mosaic Đa Kênh & Invariant Soi Mắt Trước Khi Gửi**: Khi chuẩn hoá $\ge 1$ kênh cùng lúc, ghép thành 1 ảnh mosaic tổng hợp (`avatar_standardization_proposals.jpg`) chia hàng theo máy, cột theo phương án. Dùng `browser_navigate("file:///...")` kết hợp `browser_vision` mở ảnh local để soi mắt kiểm tra (xác nhận đúng chủ thể, không lẹm cằm/đỉnh đầu, không lỗi hiển thị đen/méo) TRƯỚC KHI gửi thẻ `MEDIA:<path>` cho Operator duyệt.
- **Quy Chuẩn Khi Operator Yêu Cầu "Gen Ava Khác" (Multi-Round Diversity Escalation)**:
  * Khi Operator yêu cầu *"gen ava khác cho tao"* hoặc tiếp tục từ chối phương án vòng 2:
    - **CẤM TUYỆT ĐỐI** chỉ nhích thêm vài giây hoặc lấy khung hình tương tự từ cùng 1-2 video cũ (time jittering hẹp).
    - **BẮT BUỘC** quét sâu mở rộng qua hàng loạt video trong kho ($F_{src}$ / $F_{vid}$ từ clip 1 đến 9+).
    - **Thuật toán xếp hạng khung hình tối ưu**: Tính diện tích khuôn mặt kết hợp độ nét qua phương sai Laplacian: `score = area * sqrt(max(sharpness, 1.0))` trên ROI khuôn mặt. Tự động bốc frame nét nhất, góc chụp chính diện/bán diện đẹp nhất của từng video.
    - **Đa dạng hóa phong cách (Archetypes)**: Bắt buộc chọn các nhân vật mang phong cách hoàn toàn khác biệt (ví dụ: PA1 Soái ca sơ mi đen lịch lãm, PA2 Nữ chính biểu cảm tự nhiên, PA3 Nam diễn viên sành điệu, PA4 Nữ sinh nụ cười sáng).
    - Ghép thành 1 mosaic 3-4 cột (`m<May>_round<N>_proposals.jpg`), ghi rõ nhãn PA 1, PA 2, PA 3, PA 4 và mô tả phong cách ngắn gọn, soi mắt qua vision/OCR kiểm chứng trước khi gửi duyệt để Operator có thể chốt nhanh gọn bằng 1 chữ số (`1`, `2`, `3`, `4`).
- **Sau khi Operator chốt phương án (Đồng bộ kho kép & Khóa bảo vệ)**:
  - **Đồng bộ kho kép (Dual-Destination Sync)**: Copy file vuông `avatar.jpg` vào CẢ HAI kho: kho render (`D:/TIKTOK-videonuoinick/<F>/avatar.jpg`) và kho gốc (`D:/video goc/<F>/avatar.jpg`).
  - **Cắm marker bảo vệ kép**: Cắm đồng thời `.manual_avatar_locked` và `.manual_hashtag_locked` ở cả 2 thư mục để ngăn cron / scheduled generator định kỳ ghi đè rác.
  - **Cập nhật sổ cái**: Cập nhật đồng bộ các cột `Keyword Video` và `Hashtag Pool` trong `Tik<N>.xlsx`.
  - **BẮT BUỘC NẠP LÊN THIẾT BỊ THẬT NGAY (CẤM CHỈ LƯU Ổ ĐĨA RỒI BÁO XONG)**:
    * Việc lưu file vào `video goc` và `TIKTOK-videonuoinick` chỉ là bước chuẩn bị dữ liệu kho, **CHƯA PHẢI là đã đổi avatar**.
    * User phản ứng gắt gao: *"? Cả 2 acc mày đã đổi avatar lồn đâu"* khi thấy ảnh Profile chụp từ máy thật vẫn mang avatar cũ.
    * BẮT BUỘC chạy launcher nạp avatar chính thức lên máy thật:
      ```powershell
      echo RUN | powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik <Tik> -ForceAvatarMachineList "<May>" -MaxParallel 1
      ```
    * **Xử lý xung đột Device Lock khi máy đang trong ca nuôi (`multi-machine-feed-session`)**:
      - Nếu máy đang bị chiếm lock bởi ca nuôi định kỳ (VD: ca 12:00 hoặc 18:00, `project: tiktok-luot nuoi acc`), TUYỆT ĐỐI CẤM force-kill tiến trình hay can thiệp ADB làm gãy luồng lướt feed và trust của dàn nick.
      - **Cơ chế Bật Canh Lock Tự Động (`--wait-lock`)**: Sử dụng runner `run_upload_avatar.py --tik <Tik> --machine <May> --wait-lock` kích hoạt qua `terminal(background=True, notify_on_complete=True, timeout=1200)`.
      - Script ngầm sẽ theo dõi `C:\Users\Kibe\.codex\device-locks\machine_<May>.lock.json` (thăm dò mỗi 5s, timeout 900s). Ngay khi feed session kết thúc và file lock biến mất, script tự động gọi `run_tiktok_upload_avatar.ps1` đẩy avatar lên thiết bị mà không làm đóng băng hay chiếm giữ session của Coordinator.
    * Chỉ được báo hoàn tất món Avatar khi đã chụp ảnh Profile xác nhận vòng tròn avatar trên app TikTok của máy thật đã thực sự đổi sang ảnh mới!

### Bước 4.1: Quy Tắc Giữ Nguyên Tên Tiếng Việt Hợp Lệ (ALREADY)
- Khi chuẩn hóa kênh, kiểm tra Tên hiển thị hiện tại trên Profile:
  * Nếu tài khoản **đã có tên tiếng Việt chuẩn người dùng thật** (ví dụ: `Vũ Thị Nam`, `Huỳnh Diễm`): **TUYỆT ĐỐI CẤM TỰ Ý ĐỔI TÊN KHÁC** (*"Kênh 2 tên tiếng việt r sửa gì nữa"*). Giữ nguyên tên, dùng cờ `--bio-only` để chỉ nạp Bio mà không đụng vào Tên.
  * Chỉ đổi tên khi tên hiện tại là tên bot cụt lủn tiếng Anh/nước ngoài (`Cleora`, `Lilyan...`) hoặc tên cụt 1 từ (`Mai`, `Thảo`, `Linh`).

### Bước 4.2: Xử Lý Profile Trống Bio & Bẫy Story Picker Trên S7
- Trên tài khoản chưa từng cài Bio (bio rỗng), TikTok ẩn nút "Sửa hồ sơ" bên dưới stats:
  * **Cạm bẫy Tọa độ `(870, 558)`**: Trên layout căn trái (avatar nằm bên phải), tọa độ `(870, 558)` chạm vào vùng avatar/balloon mở popup *"Thêm vào Nhật ký"* (Story picker `UNKNOWN`), CẤM bấm vào!
  * **Giải pháp chuẩn xác**: Bấm trực tiếp vào chip `+ Thêm tiểu sử` tại tọa độ tâm `(220, 686)` (nhận diện qua regex `tieu\s*su|tid\w{0,2}\s*s\w{0,2}|\+\s*them`).
  * Mở màn hình `BIO_EDIT`, gõ Bio qua AdbKeyboard Base64 UTF-8 và bấm Lưu.
  * Sau khi có Bio, TikTok tự động kích hoạt hiển thị nút "Sửa hồ sơ" (`(210, 686)` hoặc `(300, 985)`), từ đó runner vào đổi Tên mượt mà.

### Bước 4.3: Kỷ Luật Điều Phối Worker & Chốt Chặn Cơ Học Sửa Code
- Khi Coordinator chạm trần direct-write T1 (10 files / 500 lines):
  * Nếu cần tạo script phụ trợ: BẮT BUỘC cấp chỉ thị `TASK_KIND: WRITE_SCRIPT` kèm budget $\le 3$ calls. CẤM subagent gọi `read_file` rà soát lung tung vì sẽ chạm trần `WORKER GATE - READ BUDGET EXHAUSTED`.
  * Nếu cần sửa code / patch file: `delegate_task` bị chốt chặn cơ học khóa cứng (`BLOCKED_BY_DISPATCH_GATE`). BẮT BUỘC dispatch qua Single Dispatch Gateway:
    `python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> --file <target_file> "<prompt 1 dòng>"`. Haiku 5.5 CLI sẽ thực hiện patch chính xác trong 15-30s.

### Bước 5: Món 4 — Bio (Tiểu sử tiếng Việt có dấu chuẩn theo Niche)
- **Phong cách Bio (Chỉ thị Operator 2026-10-18)**: *"Viết bio kiểu hài hước nhé"*.
  - BẮT BUỘC viết theo đúng **Niche kênh** (`Keyword Video` từ `Tik<N>.xlsx`).
  - Ưu tiên phong cách **Hài hước, dí dỏm, Gen Z đời thường**, có emoji sinh động (VD: Nấu ăn -> *"Nấu ăn thì ngon, mỗi tội rửa bát thì lười 🍳"*; Thể thao -> *"Tập gym để ăn nhiều hơn mà không cảm thấy tội lỗi 🏋️"*; Sức khỏe -> *"Quyết tâm sống healthy, nhưng đồ ăn vặt không cho phép 🍟"*).
  - CẤM TUYỆT ĐỐI viết bio văn mẫu khô khan, cấm viết trùng một câu bio cho nhiều tài khoản (dấu hiệu bot lộ liễu).
- **Invariant Bio Tiếng Việt Có Dấu & Cạm Bẫy Font OpenCV (User Phản Ứng: 'Ủa bio t ép ghi tiếng việt có dấu r mà?')**:
  * 100% Bio nạp lên thiết bị hoặc đề xuất cho Operator BẮT BUỘC là **TIẾNG VIỆT CÓ DẤU ĐẦY ĐỦ**, có emoji sinh động.
  * **Cạm bẫy OpenCV (`cv2.putText`)**: Hàm vẽ chữ của OpenCV chỉ hỗ trợ bảng mã ASCII. Khi vẽ proposal canvas tóm tắt, nếu lột dấu tiếng Việt (`Tu hao su thi...`) sẽ khiến Operator hiểu lầm là bot gõ không dấu lên máy!
  * **Kỷ luật trình bày**:
    1. Trong văn bản báo cáo chat: BẮT BUỘC ghi rõ nguyên văn Bio tiếng Việt có dấu chuẩn.
    2. Trong ảnh proposal nếu có chữ tiếng Việt: BẮT BUỘC dùng thư viện `PIL` (`ImageDraw` + `ImageFont.truetype`) với font Unicode hệ thống (Arial, Tahoma, Roboto), CẤM dùng `cv2.putText` lột dấu.
- Kỹ thuật nạp Bio lên Android S7 & Cạm bẫy Tọa độ Bút chì:
  - **Bẫy Tọa độ Bút chì trên TikTok v47 (Layout trống Bio)**: Trên các tài khoản chưa có Bio, TikTok ẩn nút "Sửa hồ sơ" bên dưới stats và chỉ hiện nút `+ Thêm tiểu sử` ở giữa. Điểm chạm duy nhất để mở trang Sửa hồ sơ là icon cây bút chì bên phải dòng Tên tại tọa độ **`(870, 558)`** (bounds `[798, 516][942, 600]`). CẤM TUYỆT ĐỐI dùng tọa độ cũ `(700, 558)` vì sẽ tap trượt vào khoảng trắng giữa tên và bút chì, dẫn đến kẹt loop PROFILE 5 lần và abort!
  - **BẮT BUỘC dùng AdbKeyboard UTF-8 Base64 Broadcast**:
    `am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <BASE64_UTF8_STRING>`.
  - CẤM dùng `adb shell input text` vì sẽ rớt dấu thanh hoặc gõ không dấu.
  - Xử lý bẫy clear text trong khung sửa tiểu sử (`ProfileEditActivity`): Chạm cuối dòng + `keyevent 123` (MOVE_END) + gửi chuỗi `keyevent 67` (DEL) để xóa sạch bio cũ trước khi nạp mới.
  - Lưu và bấm Back về Profile để refresh cache.

## 3. Nghiệm Thu & Visual Evidence (Gate 6)
- BẮT BUỘC chụp ảnh màn hình Profile sau khi hoàn tất cả 4 món.
- Soi mắt qua vision / OCR kiểm chứng:
  1. Avatar mới hiển thị đúng, không méo hay lẹm viền tròn.
  2. Video top view đã mang nhãn đỏ "Đã ghim".
  3. Dòng Bio hiển thị tiếng Việt có dấu đầy đủ, sắc nét, không lỗi font.
- Gửi ảnh nghiệm thu duy nhất kèm báo cáo súc tích:
  `MEDIA:<path_anh_nghiem_thu>`.

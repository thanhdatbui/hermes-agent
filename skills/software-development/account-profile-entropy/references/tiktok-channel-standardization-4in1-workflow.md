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

### Bước 3: Món 2 — Hashtag & Niche
- **Bẫy Niche Desync giữa Sổ Cái và Video Thực Tế**: Cột `Keyword Video` trong `Tik<N>.xlsx` thường bị lưu vết cũ hoặc generic (VD: `Thú vị`, `Nhảy` nhưng video thực tế là Gym hoặc Phim ngắn học đường). BẮT BUỘC đối soát trực tiếp hình ảnh clip trên grid Profile của kênh trước khi chốt ngách; TUYỆT ĐỐI CẤM tin mù quáng vào cột Keyword trong Excel.
- Đối soát nội dung clip thực tế trên kênh để cập nhật đúng ngách và pool hashtag chuẩn:
  - Cắm marker `.manual_hashtag_locked` trong thư mục video render $F_{vid}$ (`D:/TIKTOK-videonuoinick/<F>/` hoặc `D:/TIKTOK-videonuoinick-admin/<F>/`).
  - Ghi nhận vào `manual_hashtag_protected_folders.json`.

### Bước 4: Món 3 — Avatar Bám Lưới & Cận Cảnh Ngũ Quan
- Trích xuất 2 phương án từ video kho nguồn $F_{src}$ / kho render $F_{vid}$:
  - Chuẩn kích thước: Vuông $512 \times 512$.
  - **Kỹ thuật trích xuất & Fallback khi Haar Cascade miss (0 face)**: Với các video tiểu phẩm/kịch hoặc hoạt hình/học đường, Haar Cascade thường trả về 0 face $\rightarrow$ BẮT BUỘC fallback sang trích xuất khung hình theo mốc thời gian (`dump_sample_frames` tại giây 2, 5, 8, 12) rồi crop tâm chủ thể (`crop_head_square`), không để quy trình bị treo.
  - Cung cấp ảnh đối sánh gồm cả ảnh vuông và mô phỏng viền tròn Profile (`make_circle_preview` với viền xanh lá).
  - **Ghép Mosaic Đa Kênh & Invariant Soi Mắt Trước Khi Gửi**: Khi chuẩn hoá $\ge 1$ kênh cùng lúc, ghép thành 1 ảnh mosaic tổng hợp (`avatar_standardization_proposals.jpg`) chia hàng theo máy, cột theo phương án. Dùng `browser_navigate("file:///...")` kết hợp `browser_vision` mở ảnh local để soi mắt kiểm tra (xác nhận đúng chủ thể, không lẹm cằm/đỉnh đầu, không lỗi hiển thị đen/méo) TRƯỚC KHI gửi thẻ `MEDIA:<path>` cho Operator duyệt.
- **Quy Chuẩn Khi Operator Yêu Cầu "Gen Ava Khác" (Re-generation Multi-Video Sweep)**:
  * Khi Operator yêu cầu *"gen ava khác cho tao"*: Tuyệt đối CẤM chỉ trích xuất các giây khác trong cùng 1 video cũ (time jittering hẹp).
  * BẮT BUỘC quét rộng qua nhiều video khác nhau trong kho ($F_{src}$ / $F_{vid}$ từ clip 1 đến 10) để bắt trúng ít nhất 3 phong cách / góc quay / nhân vật / bối cảnh hoàn toàn khác biệt (VD: nhân vật học sinh đồng phục vs nhân vật tiểu phẩm vs biểu cảm kịch tính/hài hước).
  * Ghép thành 1 mosaic hàng ngang 3 cột (`m<May>_new_avatar_proposals.jpg`), ghi rõ nhãn PA 1, PA 2, PA 3 và chú thích ngắn gọn, soi mắt qua vision kiểm chứng trước khi gửi duyệt.
- **Sau khi Operator chốt phương án (Đồng bộ kho kép & Khóa bảo vệ)**:
  - **Đồng bộ kho kép (Dual-Destination Sync)**: Copy file vuông `avatar.jpg` vào CẢ HAI kho: kho render (`D:/TIKTOK-videonuoinick/<F>/avatar.jpg`) và kho gốc (`D:/video goc/<F>/avatar.jpg`).
  - **Cắm marker bảo vệ kép**: Cắm đồng thời `.manual_avatar_locked` và `.manual_hashtag_locked` ở cả 2 thư mục để ngăn cron / scheduled generator định kỳ ghi đè rác.
  - **Cập nhật sổ cái**: Cập nhật đồng bộ các cột `Keyword Video` và `Hashtag Pool` trong `Tik<N>.xlsx`.
  - Nạp avatar lên thiết bị bằng launcher chuẩn:
    `python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <Tik> --machine <May>`.

### Bước 4.1: Kỷ Luật Điều Phối Worker Tạo Script Phụ Trợ (Zero-Read Script Generation)
- Khi Coordinator chạm trần direct-write T1 (10 files / 500 lines) và cần dispatch subagent tạo script phụ trợ:
  * BẮT BUỘC cấp chỉ thị `TASK_KIND: WRITE_SCRIPT` kèm budget $\le 3$ calls.
  * CẤM subagent gọi `read_file` rà soát lung tung vì sẽ chạm trần `WORKER GATE - READ BUDGET EXHAUSTED` (tối đa 8 read calls).
  * Subagent chỉ thực hiện đúng 1 thao tác `write_file` để ghi code trọn gói, sau đó trả về ngay để Coordinator gọi thực thi trong môi trường có đủ dependencies.

### Bước 5: Món 4 — Bio (Tiểu sử tiếng Việt có dấu chuẩn theo Niche)
- **Phong cách Bio (Chỉ thị Operator 2026-10-18)**: *"Viết bio kiểu hài hước nhé"*.
  - BẮT BUỘC viết theo đúng **Niche kênh** (`Keyword Video` từ `Tik<N>.xlsx`).
  - Ưu tiên phong cách **Hài hước, dí dỏm, Gen Z đời thường**, có emoji sinh động (VD: Nấu ăn -> *"Nấu ăn thì ngon, mỗi tội rửa bát thì lười 🍳"*; Thể thao -> *"Tập gym để ăn nhiều hơn mà không cảm thấy tội lỗi 🏋️"*; Sức khỏe -> *"Quyết tâm sống healthy, nhưng đồ ăn vặt không cho phép 🍟"*).
  - CẤM TUYỆT ĐỐI viết bio văn mẫu khô khan, cấm viết trùng một câu bio cho nhiều tài khoản (dấu hiệu bot lộ liễu).
- Kỹ thuật nạp Bio lên Android S7:
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

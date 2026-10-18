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
- Đối soát nội dung clip thực tế trên kênh với cột `Keyword Video` và `Hashtag Pool` trong `Tik<N>.xlsx`.
- Đồng bộ marker bảo vệ:
  - Cắm marker `.manual_hashtag_locked` trong thư mục video render $F_{vid}$ (`D:/TIKTOK-videonuoinick/<F>/` hoặc `D:/TIKTOK-videonuoinick-admin/<F>/`).
  - Ghi nhận vào `manual_hashtag_protected_folders.json`.

### Bước 4: Món 3 — Avatar Bám Lưới & Cận Cảnh Ngũ Quan
- Trích xuất 2 phương án từ video kho nguồn $F_{src}$ / kho render $F_{vid}$:
  - Chuẩn kích thước: Vuông $512 \times 512$.
  - Cung cấp ảnh đối sánh gồm cả ảnh vuông và mô phỏng viền tròn Profile (`make_circle_preview`).
  - Soi mắt kiểm định qua `browser_vision` / WinRT OCR trước khi gửi `MEDIA:<path>` cho Operator duyệt.
- Sau khi Operator chốt phương án:
  - Đồng bộ file `avatar.jpg` vào kho nguồn và kho render.
  - Cắm marker `.manual_avatar_locked` và đăng ký vào `manual_avatar_protected_folders.json`.
  - Nạp avatar lên thiết bị bằng launcher chuẩn:
    `python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <Tik> --machine <May>`.

### Bước 5: Món 4 — Bio (Tiểu sử tiếng Việt có dấu chuẩn)
- Đề xuất 2-3 mẫu tiểu sử ngắn gọn, phù hợp với ngách nội dung của kênh (thời sự, hài hước, nấu ăn, thú cưng, gym...).
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

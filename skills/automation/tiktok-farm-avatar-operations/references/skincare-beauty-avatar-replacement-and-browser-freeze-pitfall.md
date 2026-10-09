# Case Study: Account @hatien15118 (Machine 11 - Tik 1, Folder 81) - Skincare/Beauty Avatar Replacement

## 1. Bối cảnh & Hiện trường
- **Tài khoản:** `@hatien15118` (Máy 11, Tik 1, `Folder Video` = 81, `video gốc` = 11).
- **Vấn đề phát hiện:**
  - Tài khoản đăng tải toàn bộ video về review mỹ phẩm, chăm sóc da, skincare ("Cô Gái Làm Đẹp" Kim Xuyến) và vlog đời sống.
  - Tuy nhiên, avatar trên TikTok của nick lại là ảnh một người đàn ông trung niên/lớn tuổi đeo kính đang thuyết trình (lệch hoàn toàn nhân khẩu học và niche của kênh).
  - Thư mục `D:\video goc\81\avatar.jpg` lưu ảnh một nam thanh niên mặc áo polo hồng mờ hạt, còn `D:\video goc\11\avatar.jpg` lưu ảnh phụ nữ trung niên tone màu tối. Cả 2 đều không đạt chuẩn đại diện cho kênh làm đẹp tươi sáng.

## 2. Quy trình xử lý chuẩn (Best Practice Workflow)

### Bước 1: Trích xuất frame ứng viên từ video sau
- Kênh đã đăng 28 video, các video sau (như `25.mp4`) phản ánh rõ nét chất lượng và visual của nhân vật chính.
- Trích xuất frame tại các timestamp đầu video ($t = 2.0s \dots 8.0s$).
- Dùng `cv2.CascadeClassifier` định vị khuôn mặt, crop vuông tỷ lệ $2.2 \times$ kích thước khuôn mặt, resize 512x512.

### Bước 2: Soi mắt bằng Vision QA (Chống treo browser daemon)
- **Pitfall treo phiên:** Tuyệt đối không dùng `browser_navigate("file://...")` để hiển thị ảnh cục bộ vì dễ vướng xung đột daemon agent-browser (`A daemon for session '...' started concurrently with different daemon configuration`).
- **Giải pháp O(1):** Đọc `NINEROUTER_API_KEY` từ `C:/Users/Kibe/AppData/Local/hermes/.env`, gửi request trực tiếp đến `http://127.0.0.1:20128/v1/chat/completions` (model `ag/gemini-3.7-flash-high`) truyền base64 ảnh composite để LLM Vision chấm điểm các Option.
- Chọn Option 2 (`crop_c_25.mp4_2s.jpg`): Khuôn mặt cười tươi rạng rỡ, nhìn thẳng ống kính, làn da căng bóng chuẩn skincare, không dính phụ đề, bố cục cân đối khi crop tròn TikTok.

### Bước 3: Đồng bộ 2 đầu kho & Reset Queue
- Đồng bộ file ảnh 512x512 vào cả 2 kho theo số thư mục `Folder Video` (81):
  1. `D:\video goc\81\avatar.jpg`
  2. `D:\TIKTOK-videonuoinick\81\avatar.jpg`
- Cập nhật SQLite `D:\Taadaa\data\tiktok_tracker.db`:
  ```sql
  UPDATE avatar_replace_queue 
  SET status = 'PENDING', last_error = NULL, updated_at = datetime('now', 'localtime')
  WHERE username = 'hatien15118';
  ```

### Bước 4: Chạy Launcher an toàn có Event-Driven Wakeup
- Dùng wrapper Python byte-stream (`capture_output=True, input=b"RUN\r\n"`) gọi `run_tiktok_upload_avatar.ps1 -Tik 1 -ForceAvatarMachineList "11" -MaxParallel 1` để tránh lỗi `UnicodeDecodeError` trên Windows.
- Gọi qua `terminal(background=True, notify_on_complete=True, timeout=300)` để hệ thống tự đánh thức khi xong, không polling sleep gây đơ session.

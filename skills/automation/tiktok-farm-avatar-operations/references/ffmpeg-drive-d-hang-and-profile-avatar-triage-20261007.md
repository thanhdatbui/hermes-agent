# Pitfall: FFmpeg I/O Hang on Drive D and Local SSD Copy Pattern (2026-10-07)

## Problem Description
Khi trích xuất khung hình avatar từ các video trong kho `D:\video goc\<folder>` hoặc `D:\TIKTOK-videonuoinick\<folder>`:
Lệnh FFmpeg (`ffmpeg -ss <sec> -i "D:\..." -frames:v 1 ...`) hoặc `cv2.VideoCapture("D:\...")` trực tiếp trên ổ D có thể bị nghẽn I/O hoặc deadlock stream seek, dẫn đến timeout 10s - 30s (`Exit 124: the command hit its timeout`).
Nguyên nhân do đặc thù ổ đĩa HDD chứa hàng chục nghìn file video media của farm, việc mở seek ngẫu nhiên (random seek) vào giữa container MP4 qua tiến trình subprocess dễ bị kẹt đọc block dữ liệu.

## Solution: Local SSD Fast-Copy Pattern
Thay vì để FFmpeg stream trực tiếp từ ổ D:
1. Dùng `shutil.copy2` (hoặc Python sequential read) copy tuần tự 2-3 file video mục tiêu sang ổ đĩa SSD cục bộ (`C:\Users\Kibe\AppData\Local\Temp\vid_temp`). Tốc độ sequential read đạt vài chục MB/s, chỉ mất ~0.2s cho 1 video ~5MB - 10MB.
2. Chạy FFmpeg trích xuất khung hình trực tiếp từ file video trên ổ C:
   ```bash
   ffmpeg -loglevel error -nostdin -y -ss 2.0 -i "C:\Users\Kibe\AppData\Local\Temp\vid_temp\1.mp4" -frames:v 1 -q:v 2 "C:\Users\Kibe\AppData\Local\Temp\frame_1.jpg"
   ```
   Thao tác trích xuất trên SSD cục bộ chỉ mất < 0.1s, hoàn toàn không bao giờ bị timeout.
3. Sau khi tạo xong avatar, dọn dẹp thư mục tạm trên ổ C.

## Quy trình 7 bước xử lý khi nhận lệnh đổi avatar từ ảnh Profile lẻ ("Đổi ava kênh này")
Khi Operator gửi 1 ảnh màn hình Profile TikTok và ra lệnh "Đổi ava kênh này":
1. **Đọc danh tính (Read Identity):** Dùng Vision API (9Router `ag/gemini-3.7-flash-high`) đọc username `@<username>` và kiểm tra nhận diện nội dung video trên lưới Profile.
2. **Xác định tọa độ Farm (Locate Machine & Slot):**
   - Query `D:\Taadaa\data\tiktok_tracker.db` (bảng `account_mapping`, `farm_account_info`, `avatar_replace_queue`) để lấy `may`, `tik`, `folder_video`, `video_goc`.
   - Đối soát với `D:\OneDrive\TaadaaData\kibe\Tik<tik>.xlsx` để xác định chính xác số folder nuôi và folder gốc.
3. **Phát hiện lệch Niche (Detect Drift):**
   - Kiểm tra file `avatar.jpg` hiện tại trên đĩa và avatar trên TikTok xem có đúng nhân vật/niche của video không. (Ví dụ: Kênh chó cảnh nhưng avatar là người/quán cafe, hoặc avatar cũ là nhân vật anime).
4. **Trích xuất & Chọn ứng viên (Candidate Selection):**
   - Áp dụng Local SSD Fast-Copy pattern để lấy frames từ nhiều video (`1.mp4`, `5.mp4`, `8.mp4`...) tại giây 2.0s - 4.0s.
   - Gửi ảnh qua Vision API để chấm điểm (score 1-10) tìm biểu cảm đẹp nhất, sắc nét, không dính chữ/watermark.
5. **Crop & Cân chỉnh chuẩn TikTok:**
   - Crop vuông 512x512, tăng nhẹ độ tương phản/ánh sáng nếu nhân vật tối màu (lông đen).
   - Tạo preview khung tròn đỏ để đảm bảo tai/mặt nằm trọn 100% bên trong vòng tròn avatar TikTok.
6. **Đồng bộ kho kép & Reset Queue:**
   - Ghi đè file avatar chuẩn vào CẢ HAI đầu kho:
     + `D:\video goc\<Folder Video>\avatar.jpg`
     + `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`
   - Update SQLite queue trong `D:\Taadaa\data\tiktok_tracker.db`:
     ```sql
     UPDATE avatar_replace_queue
     SET status = 'PENDING', last_error = NULL, updated_at = datetime('now', 'localtime')
     WHERE username = '<username>';
     ```
7. **Bằng chứng thị giác (Visual Evidence):**
   - Tạo ảnh composite đối chiếu Before (Ảnh Profile cũ lệch niche) vs After (Preview avatar mới trong khung tròn TikTok).
   - Dùng Vision API soi mắt kiểm tra trước khi xuất thẻ `MEDIA:<path>` cho User.

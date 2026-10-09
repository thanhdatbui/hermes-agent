# Case Study: Douyin Filter Avatar Mismatch & Video Face Selection (Machine 14 Tik 3 @nguyenlinh04011)

## Overview
Khi Operator gửi ảnh màn hình profile TikTok từ điện thoại cá nhân (iOS) với lệnh ngắn gọn: *"Đổi ava acc này cho t"*, quy trình định danh O(1), audit phát hiện lệch niche/filter, trích xuất avatar chân thực từ video gốc và khởi chạy standalone avatar runner.

---

## 1. Định danh O(1) Tài Khoản & Bản Đồ Farm
- **Dữ liệu từ ảnh chụp:**
  - Handle: `@nguyenlinh04011`
  - Display Name: `nguyenlinh0401`
- **Truy vấn SQLite O(1) (`D:/Taadaa/data/tiktok_tracker.db`):**
  - Bảng `snapshots` & `account_mapping`: `('nguyenlinh04011', 14, 3)` $\to$ **Máy 14, Slot Tik 3**.
  - Bảng `avatar_replace_queue`: `folder_video='107'`, `video_goc='174'`.
- **Đối soát Workbook `Tik3.xlsx`:**
  - Dòng Máy 14: Serial `ad061603104ee741e2`, Folder Video `107`, Video Gốc `174`, Niche: `Hài hước`.

---

## 2. Phát Hiện Lệch Vibe: Avatar Filter Douyin vs Kênh Vlog/Hài Thật
- File avatar hiện tại trong `D:\TIKTOK-videonuoinick\107\avatar.jpg`:
  - Soi qua Vision API (`ag/gemini-3.7-flash-high` qua 9Router): Ảnh chân dung nữ trang điểm Douyin cực đậm, đeo lens xám, mi giả dày, mũi bắt sáng, môi bóng.
  - Trong khi đó, video thật trên kênh là các tiểu phẩm hài hước, vlog đời thường, dã ngoại, thú cưng của một bạn nữ Việt Nam mộc mạc.
  - Avatar filter Douyin tạo cảm giác nick ảo/bot rác, mất hoàn toàn độ tin cậy tự nhiên của tài khoản.

---

## 3. Quy Trình Trích Xuất & Chọn Khung Hình Chân Dung Cận Cảnh
1. **Quét đa video trong thư mục video gốc (`D:\video goc\174`):**
   - Không chỉ lấy video 1 (`1.mp4`) vì video 1 có thể chụp góc từ trên cao (high-angle) dính bàn tay chỉnh mũ của người khác.
   - Video 6: Dính caption/phụ đề đám cưới (*"Trộm vía tàn tiệc..."*).
   - Video 8: Góc máy bước cầu thang bị cụt đầu (mất mặt).
   - Video 46: Góc quay thấp, cầm kìm kỹ thuật biểu cảm meme.
   - **Video 25 (`25.mp4`):** Bạn nữ mặc áo sơ mi ca-rô, thắt bím tóc hai bên, đội nón vành dã ngoại, nụ cười tươi rạng rỡ trực diện ống kính.
2. **Chọn timestamp chuẩn qua phân tích độ nét (Laplacian Sharpness):**
   - Trích xuất frame tại `sec=2.0s` (hoặc `sec=7.0s`): khuôn mặt đạt độ nét cao nhất, không bị nhòe chuyển động (motion blur).
3. **Crop chân dung cân đối (Square Crop with Headroom):**
   - Dùng OpenCV Haar Cascade phát hiện tâm mặt `(fx, fy, fw, fh)`.
   - Tính kích thước hộp `box_size = int(1.35 * max(fw, fh))`.
   - Căn chỉnh tâm Y hơi thấp hơn (`cy - int(box_size * 0.45)`) để giữ trọn vẹn nón và tóc.
   - Resize về `512x512` bằng `Image.Resampling.LANCZOS`, tăng nhẹ Sharpness (`1.25`) và Contrast (`1.06`).
4. **Kiểm tra tiêu chuẩn qua Vision API (Đạt 8.0/10 - 8.5/10):**
   - 100% không dính chữ, không logo/phụ đề.
   - Ngũ quan rõ ràng, biểu cảm thân thiện, nhận diện tốt ngay cả khi thu nhỏ trong vòng tròn TikTok.

---

## 4. Đồng Bộ 4 Đầu Kho & Kích Hoạt Thiết Bị Thật
1. **Đồng bộ 4 đầu kho đĩa:**
   - Khi `Folder Video` (`107`) khác `Video Gốc` (`174`), bắt buộc copy avatar mới vào cả:
     - `D:\TIKTOK-videonuoinick\107\avatar.jpg`
     - `D:\video goc\107\avatar.jpg`
     - `D:\video goc\174\avatar.jpg`
     - `D:\TIKTOK-videonuoinick\174\avatar.jpg`
2. **Reset SQLite Queue:**
   - `UPDATE avatar_replace_queue SET status='PENDING', last_error=NULL, updated_at=datetime('now','localtime') WHERE username='nguyenlinh04011';`
3. **Preflight Thiết Bị Samsung S7 Máy 14:**
   - Kiểm tra `dumpsys power`: nếu màn hình `state=OFF`, đánh thức ngay `input keyevent 224`.
   - Dọn RAM: buộc dừng Chrome, Instagram, Facebook, Google Photos để tránh treo TikTok trên S7.
4. **Khởi chạy Standalone Runner:**
   - Kích hoạt `run_tiktok_upload_avatar.ps1` với `-Tik 3 -ForceAvatarMachineList 14 -MaxParallel 1`.
   - Chạy nền có thông báo kết thúc (`notify_on_complete=True`).

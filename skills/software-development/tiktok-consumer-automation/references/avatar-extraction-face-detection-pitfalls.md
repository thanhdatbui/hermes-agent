# Kinh nghiệm & Cạm bẫy Avatar Extraction và TikTok Profile Upload

## 1. Cạm bẫy trích xuất khuôn mặt làm Avatar từ Video (OpenCV Haar Cascade Pitfall)
* **Hiện tượng:** Trích xuất nhầm icon UI ở mép màn hình (đặc biệt là icon đĩa nhạc xoay TikTok ở góc dưới bên phải `x > 0.8*w, y > 0.7*h` hoặc icon avatar kênh ở cạnh phải). Khi phóng to, icon tròn bị nhận diện nhầm là khuôn mặt (false positive) hoặc crop trúng cảnh cosplay, đồ họa game anime, dẫn đến avatar dị dạng không có người thật.
* **Quy tắc trích xuất bắt buộc:**
  1. **Crop Boundary Guard (Bỏ qua mép UI):** Chỉ quét và chấp nhận khuôn mặt nằm trong vùng trung tâm khung hình:
     - `0.2 * width < cx < 0.8 * width`
     - `0.15 * height < cy < 0.75 * height`
  2. **Min Face Size:** `minSize=(140, 140)` trên video 1080x1920 để đảm bảo bắt trúng chủ thể chính diện, không bắt icon nhỏ.
  3. **Lọc nội dung Cosplay / Anime:** Trước khi tải/gán kênh độc quyền, quét tiêu đề/tags loại bỏ các từ khóa cosplay/game như `cosplayer`, `genshin`, `anime`, `hoathinh`, `game`.

## 2. TikTok 47.x UI Layout Compatibility (Profile Header & Pencil)
* **Vị trí Avatar mới:** Trên TikTok build 47.x (Samsung S7), vòng tròn avatar không còn ở chính giữa mà dời sang góc trên bên phải cạnh tên handle (`x: 800..1040, y: 350..600`).
* **Vòng tròn giữa có dấu cộng:** Vòng tròn ở trung tâm là nút "Thêm vào Nhật ký" (Story). Bấm vào đây sẽ mở trình chọn video đăng Story thay vì sửa hồ sơ.
* **Nút Sửa Hồ Sơ (Top-Left Pencil):**
  - Icon bút chì nằm ở góc trên bên trái: bounds `[24,96][126,204]`, tâm `(75, 150)`.
  - Phải ưu tiên tap vào icon này để mở trực tiếp màn hình Sửa hồ sơ (`Edit Profile` / `Thay đổi ảnh`), tránh tap nhầm vòng tròn giữa.

## 3. Xung đột Cronjob dọn Cache (Clear Cache Watchdog Mutex)
* **Hiện tượng:** Khi bot đang trong tiến trình chọn ảnh hoặc upload avatar lên CDN, nếu cronjob `cron_clear_tiktok_cache.py` chạy ngầm kích hoạt mở widget/menu dọn rác sẽ làm crash/che màn hình TikTok và hủy network request upload.
* **Giải pháp:** Phải kiểm tra và tạm pause hoặc acquite lock thiết bị trước khi chạy các batch upload nhạy cảm.

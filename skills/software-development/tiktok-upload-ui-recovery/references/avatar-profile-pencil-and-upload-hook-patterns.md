# Avatar Profile Pencil UI & Upload Hook Patterns

## 1. Proxy Password URL-Encoding
Nếu proxy password chứa ký tự đặc biệt như `#`, `!` (ví dụ `TaadaaMobi#2026!`):
- Bắt buộc phải URL-encode bằng `urllib.parse.quote(pwd, safe="")` -> `TaadaaMobi%232026%21`.
- Nếu để raw chuỗi URL `http://user:TaadaaMobi#2026!@host:port`, yt-dlp và curl sẽ parse sai và văng lỗi `407 Proxy Authentication Required` hoặc `Failed to parse`.

## 2. Upload Hook chạy ở phiên cuối ca nuôi (`multi_machine_feed_session.py`)
- **Import path:** Dùng `from python_runner.flows.upload_preflight import ...` với fallback `from flows.upload_preflight import ...` để tránh `ModuleNotFoundError: No module named 'flows'` khi chạy từ repo root.
- **OneDrive File Lock:** File workbook trên `D:\OneDrive\TaadaaData\kibe` hay bị sync lock 1-2s, hàm đọc `openpyxl` bắt buộc bọc retry 3 lần kèm delay `time.sleep(1.5)` để tránh `PermissionError`.
- **Case-insensitive output verification:** Kiểm tra `stdout.lower()` với các biến thể `"post verification passed"`, `"upload video success"`, `"upload completed"`, đồng thời capture `stderr_tail` vào `upload_result.json`.

## 3. TikTok UI Mới - Nút "Sửa hồ sơ" biến mất & Bẫy Mở Nhầm Story Nhật Ký (2026-09-24)
- Trên các phiên bản TikTok mới (47.x trên Samsung S7 1080x1920):
  - **BẪY STORY NHẬT KÝ (STORY PICKER TRAP)**: Bấm trực tiếp vào vòng tròn avatar trên màn Profile cá nhân (`bounds=[708,300][1080,636]` hoặc `(540, 336)`) KHÔNG mở màn hình sửa avatar, mà mở màn hình **"Thêm vào Nhật ký"** (Tạo story).
  - Nút chữ "Sửa hồ sơ" lớn ở giữa profile không còn hiển thị.
  - **VỊ TRÍ CHUẨN ĐỂ MỞ "SỬA HỒ SƠ"**:
    * **Biểu tượng cây bút góc trên bên trái** (Top-Left Pencil icon): nằm tại `bounds=[24,96][126,204]`, tọa độ tâm `(75, 150)`. Bấm nút này sẽ mở trực tiếp màn hình "Sửa hồ sơ" 100%.
    * Phụ trợ: Biểu tượng cây bút bên phải tên hiển thị (`bounds` vùng `[815,205][959,289]`).
- Quy trình cập nhật Avatar qua UI mới:
  1. Tap nút cây bút góc trên bên trái `(75, 150)` -> Vào thẳng màn "Sửa hồ sơ".
  2. Tap avatar ở giữa `[396,552][683,609]` -> Mở bottom sheet chọn menu "Tải ảnh lên" `[0,1559][1080,1715]`.
  3. Chọn ảnh đầu tiên trong grid "Gần đây" (`/sdcard/Pictures/`) -> Tap "Tiếp" `[780,1788][1044,1896]`.
  4. Màn crop/nhật ký: Bỏ chọn "Đăng ảnh này lên Nhật ký" nếu không cần story -> Tap "Lưu" `[552,1728][1032,1860]`.
  5. Back về màn Profile và xác nhận avatar đã cập nhật.

## 4. Kiểm Chuẩn Chất Lượng Avatar (Face Detection & Chống Bẫy Khung Hình Đen / Mất Mặt)
- **CẠM BẪY KHUNG HÌNH TỐI ĐEN (DARK FRAME TRAP)**:
  - Nếu chỉ dùng `ffmpeg -ss 00:00:03` cắt frame ngẫu nhiên, rất dễ rơi trúng khung hình chuyển cảnh (fade to black) hoặc đoạn intro nền tối (mean BGR ~ 20-30), khiến avatar upload lên bị tối thui và user phàn nàn "không thấy người trong avatar".
- **QUY CHUẨN TRÍCH XUẤT AVATAR MẶT NGƯỜI**:
  1. Rà soát video qua nhiều mốc thời gian ($1.0s, 2.0s, 2.5s, 4.0s$).
  2. Dùng OpenCV Haar Cascade Face Detection (`haarcascade_frontalface_default.xml`) để định vị khuôn mặt người:
     ```python
     faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
     ```
  3. Kiểm tra độ sáng trung bình (`mean_brightness >= 80` và `<= 200`).
  4. Cắt vuông xung quanh khuôn mặt lớn nhất với tỉ lệ mở rộng $1.8 \times - 2.0 \times$ kích thước mặt để lấy trọn vẹn chân dung, sau đó resize về chuẩn `(512, 512)` JPEG chất lượng 95.

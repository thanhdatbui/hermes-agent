# Quy trình Khóa Avatar Thủ công & Ưu tiên Trích xuất từ Video Gốc (2026-10-10)

## 1. Chỉ thị Ưu tiên Video Gốc khi Trích xuất Avatar ("Lấy từ video gốc ấy đừng lấy từ render")
- **Bối cảnh:** Khi folder nuôi nick (`D:\TIKTOK-videonuoinick\<Folder Video>`) chứa video đã qua xử lý render (thêm viền, hiệu ứng zoom, chỉnh màu, lọc vignette hoặc chèn banner/sub), việc cắt avatar từ clip render dễ làm ảnh chân dung bị:
  * Ám viền tối / vignette nặng ở 4 góc.
  * Bệt màu, vỡ hạt do nén nhiều lần (re-encoding).
  * Dính logo, watermark, phụ đề vietsub hoặc banner trang trí.
- **Quy tắc trích xuất từ Video Gốc (`D:\video goc\<Video Gốc>`):**
  * Tra cứu cột `video gốc` trong workbook tương ứng (ví dụ Máy 26 Tik 1 $\to$ Folder Video 201, Video Gốc 26).
  * Mở kho thô nguyên bản (`D:\video goc\26\`) để trích xuất frame trực tiếp từ video gốc (như `38.mp4` tại 4.5s).
  * Video gốc giữ nguyên độ phân giải cảm biến camera, không có phụ đề hay watermark của bên thứ ba, màu da và ánh sáng đạt độ trung thực cao nhất.
  * Thẩm định qua Vision API: độ sắc nét mắt/mi/môi, biểu cảm trực diện, headroom 8-12%, đạt điểm $\ge 9.0/10$ trước khi crop 512x512.

---

## 2. Cơ chế Khóa Avatar 4 Lớp ("Khoá ava lại tránh batch upload hoặc khi sửa ava hàng loạt tạo lại ava mới")
Sau khi hoàn tất đổi avatar thủ công cho một tài khoản theo yêu cầu của Operator, BẮT BUỘC phải kích hoạt đủ 4 lớp khóa bảo vệ để không bị các batch script vô tình đè mất:

### Lớp 1: Khóa Thiết Bị Khỏi Batch Upload Avatar & Cron Watchdog
- **Workbook (`Tik<N>.xlsx`):** Cập nhật cột `Avatar = 'OK'`. Script điều phối máy cần up avatar (`resolve_avatar_pending_machines.py`) lọc theo điều kiện `Avatar != 'OK'`, do đó khi đã `OK`, batch runner tự động bỏ qua máy này.
- **Database (`tiktok_tracker.db`):** Cập nhật `avatar_replace_queue`:
  ```sql
  UPDATE avatar_replace_queue
  SET status = 'DONE', last_error = NULL, updated_at = datetime('now', 'localtime')
  WHERE username = '<username>';
  ```
  Watchdog ca tối (`post_evening_avatar_watchdog.py`) chỉ bốc các dòng có `status = 'PENDING'`, đảm bảo không kích hoạt up lại lên thiết bị.

### Lớp 2: Khóa Khỏi Tool Tái Sinh / Quét Avatar Hàng Loạt (`manual_avatar_guard.py`)
- Các tool tái tạo avatar tự động toàn farm (`regenerate_unique_avatars.py`) tích hợp module `manual_avatar_guard.py`.
- Module này đọc cấu hình từ:
  * `D:\Taadaa\Tiktok-video\data\manual_avatar_protected_folders.json`
  * `D:\Taadaa\data\manual_avatar_protected_folders.json`
- BẮT BUỘC thêm cả số folder render (`201`) và số video gốc (`26`) vào mảng `protected_folders` và cập nhật thông tin trong `accounts`:
  ```json
  "protected_folders": [..., 26, 201],
  "accounts": {
    "201": {
      "username": "trn.m.m620",
      "machine": 26,
      "tik": 1,
      "video_goc": 26,
      "description": "Gái xinh VN creator Trần Mỹ Mỹ (video 38.mp4 @ 4.5s)",
      "updated_at": "2026-10-10 11:51:00"
    }
  }
  ```
- Khi script hàng loạt quét qua, hàm `is_folder_avatar_protected(folder)` trả về `True` $\to$ bỏ qua với cờ `SKIPPED_MANUAL_PROTECTED`.

### Lớp 3: Marker Khóa Vật Lý Tại Thư Mục (`.manual_avatar_locked`)
- Tạo file cờ rỗng `.manual_avatar_locked` tại tất cả các đầu thư mục liên quan:
  * `D:\TIKTOK-videonuoinick\<Folder Video>\.manual_avatar_locked`
  * `D:\video goc\<Folder Video>\.manual_avatar_locked`
  * `D:\video goc\<Video Gốc>\.manual_avatar_locked`
- `manual_avatar_guard.py` quét in-folder marker này như một lớp phòng thủ độc lập nếu file JSON cấu hình bị thiếu hoặc hỏng.

### Lớp 4: Đồng Bộ Dual-Farm Sang Máy Chủ Admin
- Chạy lệnh đồng bộ SCP sang trạm Admin Remote (`admin-farm:D:/Taadaa/data/`):
  * `scp D:\Taadaa\data\manual_avatar_protected_folders.json admin-farm:D:/Taadaa/data/manual_avatar_protected_folders.json`
  * `scp D:\Taadaa\data\tiktok_tracker.db admin-farm:D:/Taadaa/data/tiktok_tracker.db`
- Giúp supervisor và cronjob bên cụm Admin cũng nhận diện đầy đủ trạng thái khóa.

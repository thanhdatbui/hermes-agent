# Phục Hồi Hàng Đợi Avatar Bị Kẹt Do MISMATCH_GOC & Khuyết Điểm Watchdog Ca Ngày Tik 1-2

## 1. Bản Chất Sự Cố (Root Cause Analysis)
- **Lỗ hổng watchdog ca đêm (`post_evening_avatar_watchdog.py`)**:
  - Hệ thống watchdog ca đêm chỉ quét các ca tối (`target_tiks = [5, 6, 7, 8, 3, 4]`).
  - Dàn **Tik 1 và Tik 2 cụm Kibe** hoàn toàn bị loại khỏi danh sách tự động quét và bốc máy chạy cuốn chiếu vào ban đêm.
- **Hiện tượng treo cờ `MISMATCH_GOC (diff=...)` kéo dài**:
  - Khi `video_goc` trong workbook (do trôi công thức cũ) lệch với `folder_video` thực tế trên đĩa, các script thẩm định đánh dấu cờ `MISMATCH_GOC` vào cột `last_error` của bảng `avatar_replace_queue` trong `tiktok_tracker.db`.
  - Các bản ghi này giữ nguyên trạng thái `PENDING` nhưng mang `last_error` dạng cảnh báo và không bao giờ được tự động reset nếu không có cơ chế dọn dẹp can thiệp. Hậu quả là hàng trăm tài khoản (140 nick trên Kibe) bị bỏ quên nhiều ngày.

## 2. Quy Trình 3 Bước Xử Lý Triệt Để MISMATCH_GOC

### Bước 1: Đồng bộ dữ liệu SQLite & Workbook
1. Cập nhật `avatar_replace_queue` trên cả 2 database (`D:/Taadaa/data/tiktok_tracker.db` và `D:/OneDrive/TaadaaData/tiktok_tracker.db`):
   ```sql
   UPDATE avatar_replace_queue 
   SET video_goc = folder_video, 
       status = 'PENDING', 
       last_error = NULL, 
       updated_at = datetime('now', 'localtime')
   WHERE last_error LIKE 'MISMATCH_GOC%';
   ```
2. Đồng bộ cột `video gốc` trong các file `Tik1.xlsx` và `Tik2.xlsx` khớp 100% với giá trị của cột `Folder Video`.

### Bước 2: Đồng bộ tệp `avatar.jpg` độc bản trên đĩa
- Kiểm tra tính độc bản của avatar (băm MD5) để đảm bảo không có 2 folder dùng chung 1 avatar.
- Đồng bộ file `avatar.jpg` hai chiều giữa:
  - `D:/TIKTOK-videonuoinick/<folder_video>/avatar.jpg`
  - `D:/video goc/<folder_video>/avatar.jpg`

### Bước 3: Khởi chạy Batch Runner cho Tik 1 & Tik 2
- Kích hoạt runner canonical với tham số an toàn USB / ADB semaphore:
  ```powershell
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik 2 -MaxParallel 8 -HostConfigPath D:\Taadaa\machine-config\kibe.yaml
  ```
- Sau khi batch kết thúc, parse file `summary.csv`, cập nhật các máy thành công sang `status = 'DONE'` và phân loại chi tiết các lỗi hiện trường còn lại (Switcher missing, Menu missing, Crop failed, Device offline).

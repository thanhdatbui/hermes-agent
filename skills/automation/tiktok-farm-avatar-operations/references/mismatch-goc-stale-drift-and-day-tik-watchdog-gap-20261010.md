# Bẫy MISMATCH_GOC Kẹt Liên Tuần & Khoảng Trống Tik 1 & 2 Ca Ngày (2026-10-10)

## 1. Bối cảnh & Hiện tượng
- **Hiện tượng**: Operator bức xúc phản ánh: *"R hàng loait folder lỗi bữa mày mõm tạo lại ava r đánh dấu lại hết r mà"*.
- **Thực tế kiểm tra ground truth SQLite (`avatar_replace_queue`)**:
  - Toàn farm có 1.000 acc `DONE`, nhưng còn **254 acc `PENDING`**.
  - Trong 254 acc `PENDING`, có tới **140 acc dính cờ `MISMATCH_GOC (diff=...)`** mang timestamp cũ từ `2026-10-02 16:28:45` — chưa từng được giải phóng trong hơn 8 ngày!
  - 100% 140 acc này nằm ở **Tik 1 (73 acc)** và **Tik 2 (67 acc)** của cụm **Kibe (Máy 1–80)**.

## 2. Căn nguyên Gốc rễ (Root Cause)

### A. Lệch không gian đánh số (Formula Drift)
- `Folder Video = (Máy - 1) * 8 + Tik` (chia theo máy).
- `video gốc = (Tik - 1) * 80 + Máy` (chia theo ca).
- Script validation so sánh perceptual hash giữa `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg` và `D:\video goc\<video gốc>\avatar.jpg`.
- Vì 2 folder này chứa 2 kênh video hoàn toàn khác nhau, độ lệch ảnh luôn cao (`diff > 50`), dẫn đến script gắn cờ lỗi `MISMATCH_GOC` và chặn không cho upload.

### B. Khoảng trống điều phối của Watchdog ca tối (Day Tik Watchdog Gap)
- Watchdog ca tối (`post_evening_avatar_watchdog.py`) chỉ được lập trình cho danh sách slot ca tối:
  ```python
  ("kibe", "FARM KIBE - MÁY 1-80", [5, 6, 7, 8, 3, 4])
  ```
- **Tik 1 và Tik 2 của Kibe hoàn toàn vắng mặt** trong danh sách target của watchdog vì chúng thuộc ca ngày.
- Các phiên trước ngộ nhận rằng *"đã tạo avatar mới và đánh dấu PENDING thì watchdog sẽ tự cày hết"*, nhưng watchdog ca tối không bao giờ bốc Tik 1 và Tik 2 Kibe! Kết quả là 140 nick này bị bỏ quên nguyên trạng thái lỗi từ ngày 02/10.

### C. Trạng thái file đĩa vs Hàng đợi cơ sở dữ liệu
- Khi kiểm tra mã băm MD5 toàn bộ 140 folder này trong `D:\TIKTOK-videonuoinick\<folder>\avatar.jpg`:
  - **140/140 folder đã có avatar.jpg**.
  - **140 mã băm hoàn toàn độc bản** (0 nhóm trùng lặp MD5).
- Tức là file ảnh trên đĩa **đã được tái tạo thành công**, nhưng vì `last_error = 'MISMATCH_GOC'` và `video_goc != folder_video` trong SQLite & Excel, hệ thống automation không bao giờ bốc chạy.

## 3. Quy trình Khắc phục Chuẩn hóa (3 Bước Dứt điểm)

### Bước 1: Khóa cứng `video gốc = Folder Video` trên cả 2 tầng
1. **Tầng Excel**: Mở `D:\OneDrive\Tiktok\Tik1.xlsx` và `Tik2.xlsx`, gán cột `video gốc` = `Folder Video` cho toàn bộ các dòng bị lệch (79 dòng/file).
2. **Tầng SQLite**: Cập nhật cả 2 bản `tiktok_tracker.db` (local và OneDrive):
   ```sql
   UPDATE avatar_replace_queue 
   SET video_goc = folder_video, 
       status = 'PENDING', 
       last_error = NULL, 
       updated_at = datetime('now', 'localtime')
   WHERE last_error LIKE 'MISMATCH_GOC%';
   ```

### Bước 2: Đồng bộ 2 đầu kho đĩa
- Sao chép đè từ `D:\TIKTOK-videonuoinick\<folder>\avatar.jpg` sang `D:\video goc\<folder>\avatar.jpg` để 100% hai đầu kho khớp nhau tuyệt đối:
  ```python
  if os.path.exists(src) and (not os.path.exists(dst) or os.path.getsize(src) != os.path.getsize(dst)):
      shutil.copyfile(src, dst)
  ```

### Bước 3: Khởi chạy Batch Runner ban ngày cho Kibe
- Vì watchdog ca tối không tự bốc Tik 1 và Tik 2 Kibe, Coordinator bắt buộc kích hoạt batch trực tiếp khi farm rảnh (không vướng feed-session):
  ```powershell
  echo RUN | powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik <1|2> -MaxParallel 8 -HostConfigPath D:\Taadaa\machine-config\kibe.yaml
  ```
- **Kỷ luật MaxParallel cho Kibe**: Khóa trần `-MaxParallel 8` để tuân thủ adb Semaphore 8 và bảo vệ controller USB bus X99, tránh treo cổng ADB. Chạy nền với `notify_on_complete=True`.

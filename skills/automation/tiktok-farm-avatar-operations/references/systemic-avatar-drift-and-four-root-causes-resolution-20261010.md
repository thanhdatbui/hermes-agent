# Systemic Avatar Quality Drift & Complete Farm Reconciliation (2026-10-10)

## 1. Bối cảnh & Phản ánh của Operator
Khi Operator chất vấn: *"Tao bảo chuẩn hoá lại hết kho ava mà sao cứ lâu lâu lòi ra nick lỗi v"* sau khi phát hiện tài khoản `@.thy.v5` (kênh nữ sinh THPT) mang avatar mẹ & bé sơ sinh:
- Các session trước ngộ nhận rằng *"đã chạy dedup 0 nhóm trùng MD5 nghĩa là cả kho đã sạch avatar"*.
- Nhưng thực tế vận hành vẫn liên tục xuất hiện các nick có avatar lệch ngách, lệch nhân khẩu học hoặc giữ nguyên ảnh rác từ thời reg nick.

---

## 2. Bốn Tử Huyệt Hệ Thống Được Bóc Tách (Root Causes)

### A. Tử huyệt đợt sinh ảnh Dedup ngày 07/10 (498 folders)
- Script `regenerate_unique_avatars.py` cũ tập trung vào việc **xóa trùng mã băm MD5** nhưng bốc nguồn từ `D:\video goc` (thư mục video thô) thay vì `D:\TIKTOK-videonuoinick` (thư mục video render thực tế đang đăng bài).
- Khi folder render (ví dụ `148`) chứa video học đường, nhưng thư mục video gốc chứa video cũ của ca cào tháng 7 (chăm sóc mẹ & bé), script đã cắt ảnh từ video thô và gán avatar mẹ & bé cho kênh nữ sinh. Ảnh đạt 0-duplicate MD5 nhưng **sai vibe và lệch ngách 100%**.

### B. Lệch công thức kép trên 923/1.254 tài khoản
- `Folder Video = (Máy - 1) * 8 + Tik` (chia theo máy).
- `video gốc = (Tik - 1) * 80 + Máy` (chia theo ca cào).
- Bot đăng bài theo `Folder Video`, nhưng các tool trích xuất avatar và đối soát perceptual hash lại đọc `video gốc`.
- Kết quả: 923 tài khoản bị lệch giữa 2 không gian số, khiến avatar bị bốc chéo nguồn của tài khoản khác.

### C. Khoảng trống Watchdog ca tối bỏ quên Tik 1 & Tik 2 Kibe
- `post_evening_avatar_watchdog.py` cấu hình cứng `target_tiks = [5, 6, 7, 8, 3, 4]`, **loại trừ hoàn toàn Tik 1 và Tik 2 cụm Kibe**.
- Dẫn đến 100 tài khoản (Tik 1: 79 acc, Tik 2: 21 acc) bị kẹt trạng thái PENDING hàng tuần mà watchdog không bao giờ bốc chạy.

### D. Lệch không đồng bộ giữa 2 đầu kho đĩa (NUOI vs GOC)
- Trong 640 folder của Kibe, có **44 folder** bị lệch file `avatar.jpg` giữa `D:\TIKTOK-videonuoinick` và `D:\video goc`.
- Khi runner tìm kiếm fallback, việc ưu tiên hoặc rớt vào `video goc` làm máy bốc phải ảnh cũ chưa được cập nhật.

---

## 3. Quy trình 4 Bước Chuẩn hoá Triệt để (Full Farm Reconciliation)

### Bước 1: Khóa cứng `video_goc = folder_video` toàn diện
1. **SQLite (`tiktok_tracker.db`)**:
   ```sql
   UPDATE avatar_replace_queue
   SET video_goc = folder_video,
       updated_at = datetime('now', 'localtime')
   WHERE folder_video != video_goc;
   ```
2. **Workbooks (`Tik1..8.xlsx`)**: Quét toàn bộ 16 file Excel (cả Kibe và Admin), cập nhật cột `video gốc` = `Folder Video`.

### Bước 2: Đồng bộ nguyên tử 100% hai đầu kho đĩa (NUOI -> GOC)
- Duyệt qua toàn bộ 640 folder `1..640`:
  - Lấy `D:\TIKTOK-videonuoinick\<folder>\avatar.jpg` làm SSOT duy nhất.
  - Sao chép đè nguyên tử qua file `.tmp.jpg` sang `D:\video goc\<folder>\avatar.jpg`.
  - Đảm bảo 640/640 folder có file ảnh đồng nhất tuyệt đối về size và hash.

### Bước 3: Vá Watchdog ca tối bao phủ trọn vẹn Tik 1..8
- Trong `post_evening_avatar_watchdog.py`:
  - Sửa `target_tiks = [5, 6, 7, 8, 3, 4]` thành `target_tiks = [1, 2, 3, 4, 5, 6, 7, 8]`.
  - Sửa `cluster_order` cho Kibe thành trọn vẹn `[1, 2, 3, 4, 5, 6, 7, 8]`.
  - Chạy regression test `pytest tests/test_avatar_edit_and_milestone.py` (39/39 PASS).
  - Đánh dấu `PENDING` cho các dòng trống trong cột Avatar của `Tik1.xlsx` và `Tik2.xlsx`.

### Bước 4: Đồng bộ Database & Workbook sang Admin Farm
- Sao chép `tiktok_tracker.db` sang `D:\OneDrive\TaadaaData\tiktok_tracker.db`.
- SCP database và workbooks sang `admin-farm:D:/Taadaa/data/` và `admin-farm:D:/OneDrive/TaadaaData/admin/`.

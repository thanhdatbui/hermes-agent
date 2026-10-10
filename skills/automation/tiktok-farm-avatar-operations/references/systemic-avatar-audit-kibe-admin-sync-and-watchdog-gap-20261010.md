# Systemic Avatar Audit, Admin Tarball Sync & Watchdog Tik Gap (2026-10-10)

## 1. Bối cảnh & Hiện tượng
Khi Operator chất vấn: *"Tao bảo chuẩn hoá lại hết kho ava mà sao cứ lâu lâu lòi ra nick lỗi v"* (điển hình như nick `@.thy.v5` - Máy 19 Tik 4 đăng clip Nữ sinh THPT nhưng avatar lại bị đổi thành ảnh Mẹ & bé sơ sinh):
Kiểm tra ground truth SQLite (`tiktok_tracker.db`) và hệ thống file trên 2 trạm Kibe & Admin phát hiện 4 nguyên nhân gốc rễ liên hoàn:
1. **Bẫy Dedup MD5 ưu tiên `video goc` cũ (Đợt 07/10):**
   - Script `regenerate_unique_avatars.py` trước đây tập trung xóa trùng mã băm MD5, bốc clip từ `D:\video goc` (thô từ tháng 7/2026, ví dụ clip Spa mẹ & bé) thay vì `D:\TIKTOK-videonuoinick` (render thực tế đăng bài từ tháng 8/2026, nữ sinh THPT).
   - Mã băm MD5 sinh ra là độc bản (0 trùng lặp), script báo cáo "sạch kho", nhưng thực chất là avatar lệch ngách hoàn toàn với video đăng bài trên kênh!
2. **Khoảng trống Watchdog Tik 1 & 2 Kibe:**
   - `post_evening_avatar_watchdog.py` cấu hình cứng `target_tiks = [5, 6, 7, 8, 3, 4]`, loại trừ hoàn toàn Tik 1 và Tik 2 của Kibe.
   - Khiến 100+ tài khoản Tik 1 & 2 Kibe bị kẹt `PENDING` hàng tuần không bao giờ được bốc chạy lên máy thật.
3. **923 tài khoản lệch công thức `folder_video` vs `video_goc`:**
   - 923 dòng trong SQLite và 16 file `Tik1..8.xlsx` bị lệch giữa `(Máy-1)*8+Tik` và `(Tik-1)*80+Máy`.
4. **Kho Media Admin thiếu trắng 407/640 avatar:**
   - Trên trạm Admin (`admin-farm`), thư mục `D:\TIKTOK-videonuoinick-admin` chỉ có 167/640 folder có `avatar.jpg`, thiếu tới 407 folders dẫn đến lỗi `NO_AVATAR` và thiết bị bốc ảnh placeholder cũ.

---

## 2. Quy trình Chuẩn hoá & Đồng bộ Dứt điểm (4 Bước)

### Bước 1: Khóa cứng `video_goc = folder_video` toàn diện
- Cập nhật SQLite:
  ```sql
  UPDATE avatar_replace_queue 
  SET video_goc = folder_video, updated_at = datetime('now', 'localtime') 
  WHERE folder_video != video_goc;
  ```
- Duyệt và cập nhật toàn bộ 16 file Excel (`D:\OneDrive\TaadaaData\kibe\Tik1..8.xlsx` và `admin\Tik1..8.xlsx`): gán cột `video gốc` = `Folder Video`.

### Bước 2: Đồng bộ 100% hai đầu kho Kibe (`TIKTOK-videonuoinick` $\to$ `video goc`)
- Quét toàn bộ 640 folders:
  - Copy đè nguyên tử các file `avatar.jpg` từ `D:\TIKTOK-videonuoinick\<N>\avatar.jpg` sang `D:\video goc\<N>\avatar.jpg`.
  - Đảm bảo 640/640 folder có ảnh độc bản chuẩn ngách.

### Bước 3: Đóng gói Tarball đồng bộ sang Admin Media Root
- Thay vì SCP từng file chậm và dễ lỗi, nén toàn bộ 640 avatar trên Kibe thành tarball:
  ```python
  with tarfile.open("kibe_avatars.tar", "w") as tar:
      for folder in sorted(root.iterdir()):
          if folder.is_dir() and folder.name.isdigit():
              av = folder / "avatar.jpg"
              if av.is_file():
                  tar.add(av, arcname=f"{folder.name}/avatar.jpg")
  ```
- SCP sang Admin và giải nén nguyên tử:
  ```bash
  scp kibe_avatars.tar admin-farm:D:/Taadaa/kibe_avatars.tar
  ssh admin-farm "python -c \"import tarfile; tarfile.open('D:/Taadaa/kibe_avatars.tar').extractall('D:/TIKTOK-videonuoinick-admin')\""
  ```
- Xác nhận nghiệm thu trên Admin: 640/640 folder đạt `Has avatar: 640`, `Missing: 0`.

### Bước 4: Mở rộng Watchdog Kibe bao quát Tik 1..8
- Trong `scripts/post_evening_avatar_watchdog.py`:
  - Đổi `target_tiks = [5, 6, 7, 8, 3, 4]` thành `target_tiks = [1, 2, 3, 4, 5, 6, 7, 8]`.
  - Đổi `cluster_order` cho Kibe sang trọn vẹn `[1, 2, 3, 4, 5, 6, 7, 8]`.
- Chạy unit test kiểm chứng: `pytest tests/test_avatar_edit_and_milestone.py` (39/39 PASS).
- Đánh dấu `PENDING` cho các dòng trống trong `Tik1.xlsx` và `Tik2.xlsx` Kibe để watchdog tự động bốc chạy khi máy nhả lock.

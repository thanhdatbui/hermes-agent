# Contract-Driven Worker Avatar Sync & End-to-End Verification (2026-10-17)

## 1. Định Vị Tọa Độ Workbook Tik<N>.xlsx
- **Vị trí file**: `Tik<N>.xlsx` thường nằm trực tiếp tại `D:/Tik<N>.xlsx` (hoặc `D:/OneDrive/TaadaaData/kibe/Tik<N>.xlsx`), **không nằm** trong `D:/Taadaa/Tiktok-video/`.
- Khi tra cứu tài khoản, ưu tiên đọc `D:/Tik<N>.xlsx` qua `openpyxl` với `data_only=True` trên sheet `TaiKhoan`:
  - `Col 1`: Số máy
  - `Col 2`: Serial ADB
  - `Col 3`: Username TikTok
  - `Col 4`: Folder video render ($F_{vid}$)
  - `Col 6`: Folder video gốc ($F_{src}$)

---

## 2. Kỷ Luật Dispatch Worker Khi Hết Ngân Sách T1 Coordinator
Khi Coordinator chạm giới hạn ngân sách T1 (5 files, 200 dòng):
- **Bẫy INVESTIGATE**: Dispatch với `TASK_KIND: INVESTIGATE` biến Worker thành **READ-ONLY 100%**, không thể ghi/sửa bất kỳ file nào (`⛔ [WORKER GATE - READ-ONLY WORKER]`).
- **Bắt buộc dùng TASK_KIND: EDIT** kèm đầy đủ 5 thành phần Guard Contract:
  1. `TASK_KIND: EDIT`
  2. `FILE: <đường_dẫn_tuyệt_đối>`
  3. `OLD_STRING: <<< ... >>>` và `NEW_STRING: <<< ... >>>`
  4. `FOCUSED_TEST: python -m pytest <path>::<node>` (ví dụ: `D:/Taadaa/tests/test_admin_ssh.py::test_command`)
  5. `FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT)...`
  6. **Diff Budget $\le 30$ dòng**: Khối `NEW_STRING` phải cô đọng, viết ngắn gọn (gộp biến, import inline) để tổng diff không vượt quá 30 dòng.

---

## 3. Quy Trình Đồng Bộ Kho & Khóa Bảo Vệ (3 Đầu Kho)
Sau khi User duyệt Phương án Avatar (ví dụ Option 1):
1. **Copy `avatar.jpg`**:
   - `D:/video goc/<F_src>/avatar.jpg`
   - `D:/video goc/<F_vid>/avatar.jpg`
   - `D:/TIKTOK-videonuoinick/<F_vid>/avatar.jpg`
2. **Khóa vật lý**:
   - Tạo marker `.manual_avatar_locked` tại cả 3 thư mục trên.
3. **Cập nhật SQLite Queue SSOT**:
   - Database: `D:/Taadaa/data/tiktok_tracker.db`
   - Bảng: `avatar_replace_queue`
   - Cập nhật: `UPDATE avatar_replace_queue SET status='PENDING', video_goc='<F_src>', folder_video='<F_vid>', updated_at=datetime('now','localtime') WHERE username='<target>' AND may=<M>;`

---

## 4. Kích Hoạt Canonical Runner & Nghiệm Thu Vision (Gate 6)
1. **Khởi chạy canonical launcher**:
   - `terminal(background=True, notify_on_complete=True, command="python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <tik> --machine <machine>", timeout=600)`
   - CẤM lồng `with_device_lock.py` bên ngoài vì runner con đã tự quản lý lock thiết bị.
2. **Hậu kiểm Artifact**:
   - Sau khi tiến trình báo exit 0, kiểm tra file `summary.csv` tại `D:\CodexRuntime\tiktok-video\batch-runs\batch_tik<tik>_*\summary.csv` (`Status: THÀNH CÔNG, Verified: True`).
   - Lấy ảnh `avatar-uploaded-confirmed.png` trong thư mục run (`D:\CodexRuntime\tiktok-video\runs\run_<serial>_<timestamp>\avatar-uploaded-confirmed.png`).
3. **Soi Mắt Kiểm Định (Gate 6 Invariant)**:
   - Dùng `browser_navigate` mở ảnh local (`file:///.../avatar-uploaded-confirmed.png`).
   - Gọi `browser_vision` xác nhận trực quan: đúng màn hình Profile, đúng tên hiển thị & username, avatar tròn đã cập nhật ảnh mới, không bị méo/chém trán/lẹm cằm hay popup che.
   - Báo cáo kèm thẻ `MEDIA:<path_to_avatar-uploaded-confirmed.png>`.
4. **Write-Through Hoàn Tất**:
   - Cập nhật `Tik<N>.xlsx` (Cột 13 -> `DONE`).
   - Cập nhật `avatar_replace_queue` trong `D:/Taadaa/data/tiktok_tracker.db` (`status='DONE'`).

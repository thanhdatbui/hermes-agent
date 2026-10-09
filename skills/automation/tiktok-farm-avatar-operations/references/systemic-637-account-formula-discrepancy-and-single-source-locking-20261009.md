# Systemic 637-Account Formula Discrepancy & Single-Source Locking (2026-10-09)

## 1. Bản chất gốc rễ: Tại sao farm "cứ bị lệch avatar hoài"?
Khi Operator bực bội hỏi: *"là sao cứ lệch hoài thế"*:
- Điều tra toàn diện 640 tài khoản trên cả 8 workbook (`Tik1.xlsx` đến `Tik8.xlsx`) phát hiện:
  **637 / 640 tài khoản (99.5%) bị lệch hoàn toàn giữa `Folder Video` và `video gốc`!**

### Nguyên nhân công thức chéo trong Excel:
1. **`Folder Video` (Thư mục render để bot upload clip):**
   - Đánh số tịnh tiến theo máy: `(Máy - 1) * 8 + Tik` (chạy từ 1 đến 640).
   - Ví dụ: Máy 62, Tik 3 $\rightarrow$ `(62 - 1) * 8 + 3` = **Folder 491**.
2. **`video gốc` (Thư mục video thô ban đầu):**
   - Đánh số chia theo cụm Tik: `(Tik - 1) * 80 + Máy`.
   - Ví dụ: Máy 62, Tik 3 $\rightarrow$ `(3 - 1) * 80 + 62` = `160 + 62` = **Folder 222**.

### Hậu quả phân mảnh công cụ (Dual-Path Drift):
- **Bot đăng video (`tiktok_workflow`):** Bốc video từ `Folder Video` (`D:\TIKTOK-videonuoinick\491`) $\rightarrow$ Kênh đăng toàn bộ clip của bạn nữ áo thể thao đỏ kính cận (Nike).
- **Tool cắt avatar / batch dedup (`regenerate_unique_avatars.py`, `_make_avatar.py`):** Lại bốc clip từ `D:\video goc\<video gốc>` (`D:\video goc\222`). Thư mục 222 là ngách tập gym của nam thanh niên đeo kính râm gồng bắp tay.
- Hậu quả: Nick mang tên nữ "Dương Chi", clip đăng toàn gái nhưng avatar bị up nhầm ảnh nam gồng cơ bắp!

---

## 2. Quy trình xử lý dứt điểm khi Operator ra lệnh "Fix đi đừng có lệch nữa"

### Bước 1: Trích xuất Avatar chuẩn từ chính Folder Video
- Tuyệt đối KHÔNG đọc `video gốc` khi có sự lệch số.
- Quét các video trong `D:\TIKTOK-videonuoinick\<Folder Video>` (hoặc `D:\video goc\<Folder Video>`):
  - Tìm frame chân dung đại diện khớp với nhân vật trong các clip đã đăng trên kênh (dùng Vision API đối chiếu với screenshot Profile grid).
  - Crop chuẩn headroom 512x512, tỷ lệ khuôn mặt 30-50%, không dính subtitle/watermark.

### Bước 2: Đồng bộ triệt để 2 đầu kho
- Copy file `avatar.jpg` mới vào:
  1. `D:\video goc\<Folder Video>\avatar.jpg`
  2. `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`
- Kiểm tra mã băm MD5 đảm bảo 2 đầu kho trùng khớp 100%.

### Bước 3: Khóa cứng sổ cái Excel & Database Queue
1. **Cập nhật Excel `Tik<N>.xlsx` dòng tài khoản:**
   - Cột `video gốc`: gán bằng chính số của `Folder Video` (ví dụ `491`) để triệt tiêu vĩnh viễn sự chênh lệch nguồn.
   - Cột `Avatar`: gán `'PENDING'`.
2. **Cập nhật SQLite `D:\Taadaa\data\tiktok_tracker.db`:**
   ```sql
   UPDATE avatar_replace_queue 
   SET status = 'PENDING', last_error = NULL, updated_at = datetime('now', 'localtime')
   WHERE may = <M> AND tik = <Tik>;
   ```

### Bước 4: Preflight thiết bị & Khởi chạy Single-Machine Runner
1. **Cấu hình chống Sleep & Wake screen:**
   ```bash
   adb -s <SERIAL> shell "settings put global stay_on_while_plugged_in 3"
   adb -s <SERIAL> shell input keyevent 224
   adb -s <SERIAL> shell input keyevent 82
   ```
2. **Khóa biến môi trường `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION`:**
   Trên trạm Kibe, `automation-core` là phiên bản `0.4.45`. Khi launcher PowerShell chạy, bắt buộc set:
   ```python
   env["TIKTOK_VIDEO_AUTOMATION_CORE_VERSION"] = "0.4.45"
   env["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\kibe.yaml"
   ```
3. **Gọi launcher chuẩn:**
   ```bash
   echo RUN | powershell.exe -NoProfile -ExecutionPolicy Bypass \
     -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 \
     -Tik <Tik> -MaxParallel 1 \
     -HostConfigPath D:\Taadaa\machine-config\kibe.yaml \
     -ForceAvatarMachineList "<M>"
   ```
   Chạy nền có `background=True, notify_on_complete=True, timeout=300`.

# Quick Reseed & Content Replacement Playbook (Cut Spare Pool -> Random Render)

Tài liệu hướng dẫn quy trình thay thế toàn bộ content/video cho một tài khoản TikTok trên farm khi phát hiện vi phạm, dính chính trị/tiêu cực hoặc đổi hướng niche mà cần hoàn thành nhanh, chuẩn xác.

## 1. Các bước thực hiện chuẩn (Deterministic Sequence)

### Bước 1: Khóa thông tin tài khoản & Xác định Mapping
- Tra cứu chính xác từ `TikN.xlsx` (hoặc `taikhoan_dat_v2_updated .xlsx` / `taikhoan_run_safe.xlsx`):
  - Machine (`Máy`), Slot (`Row 1..8` / `Tik1..Tik8`).
  - Source folder (`D:\video goc\<video_goc>`).
  - Render folder (`D:\TIKTOK-videonuoinick\<Folder Video>`).
  - Exact handle (username).

### Bước 2: Dọn sạch & Reset trạng thái (Destructive Clean)
1. **Xóa toàn bộ file trong Source folder**: `D:\video goc\<source_id>` (bao gồm cả `.avatar_work`).
2. **Xóa toàn bộ file trong Render folder**: `D:\TIKTOK-videonuoinick\<folder_video>` (bao gồm cả file render cũ và avatar).
3. **Dọn dẹp post-attempts ledger**: Xóa sạch các file JSON trong `D:\CodexRuntime\tiktok-video\idempotency\post-attempts\` liên quan đến `machine_<M>_account_<handle>*` hoặc `machine_<M>_video_*` để tránh bị chặn idempotency/duplicate upload.
4. **Reset counters trong Workbooks**:
   - Backup `TikN.xlsx` và `taikhoan_run_safe.xlsx`.
   - Đặt `Video Đã Đăng = 0` ở cả 2 workbook để upload runner bắt đầu lại từ `1.mp4`.
   - Cập nhật niche mới tại cột `Keyword Video` và pool hashtag mới tại `Hashtag Pool` (sheet `TaiKhoan` và sheet `Hashtag theo Folder`).

### Bước 3: Cắt nguồn sạch từ Spare Pool (Destructive CUT)
- Tìm một folder nguồn dự phòng trong `D:\video goc\` (chưa từng gán cho máy nào trong Tik1..Tik8, thường >235 hoặc >480) có $\ge 45$ video mp4 hợp lệ và có `avatar.jpg`.
- Di chuyển toàn bộ file (`shutil.move`) từ folder spare sang thư mục nguồn của nick đích (`D:\video goc\<video_goc>`).
- Xác nhận folder spare cũ đã sạch 0 file (tránh 2 nick trùng video).

### Bước 4: Chạy Random Render Local (`random_batch_render.py`)
- Lập file danh sách video cần render bằng `select_videos()` (30..45 video).
- Chạy render với `--randomize` để phá mã băm (MD5 / pHash / Audio Fingerprint):
  ```bash
  cd /d/Taadaa/Tiktok-video && \
  "D:/Taadaa/python-envs/automation/Scripts/python.exe" -u scripts/random_batch_render.py \
    --input-dir "D:\video goc\<video_goc>" \
    --file-list "D:\CodexRuntime\tiktok-video\batch-runs\source-<video_goc>-reseed.txt" \
    --output-dir "D:\TIKTOK-videonuoinick\<Folder Video>" \
    --preset "presets\preset_owner.json" \
    --run-id "kibe-m<M>-slot<S>-reseed" \
    --randomize \
    --slot <S-1> \
    --machine-id <M-1> \
    --seed-offset 0 \
    --parallel 1
  ```
- Kiểm định nghiệm thu: Toàn bộ output `1.mp4..N.mp4` trong `D:\TIKTOK-videonuoinick\<Folder Video>` phải vượt qua `ffprobe` (duration > 0, size hợp lệ) và có `avatar.jpg`.

### Bước 5: Cơ chế Random Hashtag khi Upload (`hashtag_selector.py`)
- Khi đăng video, hệ thống tự động bốc 3–5 hashtag từ `Hashtag Pool` của workbook, ưu tiên hashtag chứa từ khóa niche và shuffle thứ tự tag trước khi điền vào caption.

### Bước 6: Cập nhật `state.db`
- Đặt lại trạng thái folder trong `state.db` thành `complete`, cập nhật đúng niche mới, platform và số lượng video.

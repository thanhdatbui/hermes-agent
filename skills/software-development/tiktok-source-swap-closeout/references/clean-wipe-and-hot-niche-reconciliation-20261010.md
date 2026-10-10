# Clean Wipe and Hot Niche Source Swap Protocol (2026-10-10)

## 1. Context & Operator Directive
Khi tài khoản có hiện tượng lệch metadata cũ (ví dụ: `Tik2.xlsx` ghi `video gốc: 81` trong khi `Folder Video: 2`, hoặc nhãn cũ `Khoa học`/`Bếp Việt` không ăn view, thư mục thô dính debris cũ) và Operator ra lệnh:
> *"Đổi content cho nick này, cào niche hot + ava ms r đổi ava mới"*
> *"Tao bảo dẹp hết nguồn cũ cào nguồn ms niche hot cho tao"*

### Kỷ luật phản xạ (Anti-Paralysis Invariant):
- **CẤM TUYỆT ĐỐI đứng hình / báo BLOCKED viện cớ lệch dữ liệu cũ:** Khi Operator đã ra lệnh đổi content / dẹp hết nguồn cũ, mục tiêu là **thay máu toàn diện (Clean Wipe & Niche Pivot)** sang 1 trong 12 Niche Hot. Lệch dữ liệu cũ không phải là lý do để dừng lại hỏi hay báo kẹt.
- **Quy chuẩn dẹp sạch:** Xóa sạch cả raw (`D:/video goc/<folder>`) và render (`D:/TIKTOK-videonuoinick/<folder>`) kèm file `avatar.jpg` cũ.
- **Khóa cứng SSOT:** Gán `video gốc = Folder Video` trong workbook `Tik<N>.xlsx` để dứt điểm triệt để lỗi lệch công thức kép.

---

## 2. Quy Trình Thi Công 5 Bước Chuẩn Hóa

### Bước 1: Dọn sạch kho cũ & Khóa số Folder
- Xóa toàn bộ file `.mp4`, `.part`, `.jpg`, `.ytdl` và các thư mục rác con trong `D:/video goc/<F>` và `D:/TIKTOK-videonuoinick/<F>`.
- Đọc số `Video Đã Đăng` hiện tại trên TikTok (ví dụ `12`). Khóa cứng `start_seq = Video Đã Đăng + 1` (ví dụ `13`). **TUYỆT ĐỐI CẤM reset bộ đếm này về 0**.

### Bước 2: Chọn nguồn & Top-up Continuation
- Đối soát kênh mục tiêu qua:
  1. `D:/OneDrive/SharedData/tiktok-video/global-ledger/Kibe.jsonl` và `Admin.jsonl` (không dính `source_claimed` hoặc `downloaded`).
  2. `C:/CodexRuntime/tiktok-video/state.db` và `D:/CodexRuntime/tiktok-video/state.db`.
  3. `D:/Taadaa/Tiktok-video/data/gaixinh_channel_claims.json`.
- Khi tải gặp tình trạng kênh thiếu vài clip so với target (ví dụ cào được 38/40 clip):
  - **CẤM hủy bỏ công tải:** Không được xóa sạch làm lại từ đầu.
  - **Cơ chế Top-up:** Bổ sung các video shorts còn lại từ chính kênh đó hoặc kênh cùng niche để đạt tối thiểu $\ge 40$ clip (`len(raw_mp4) >= 40`).

### Bước 3: Render phái sinh bắt đầu từ `start_seq`
- Render toàn bộ video thô mới thành các video dọc chuẩn 1080x1920 (`preset_owner.json`).
- Đánh số tệp: Từ `start_seq.mp4` (ví dụ `13.mp4` đến `60.mp4` cho 48 clip).
- Kiểm tra tính toàn vẹn: Dung lượng mỗi file render phải $> 300\text{ KB}$ và có video stream hợp lệ.

### Bước 4: Tạo Avatar mới & Đồng bộ 2 đầu kho
- Cắt frame rõ nét từ video thành phẩm (ví dụ video 2, 4, 8 tại giây 3-7s), kiểm tra bằng WinRT OCR / Vision để đảm bảo không dính subtitle vietsub lẹm hoặc chữ banner to.
- Crop vuông tâm 512x512, xuất JPEG quality 95.
- Đồng bộ nguyên tử vào cả 2 đầu kho:
  1. `D:/video goc/<F>/avatar.jpg`
  2. `D:/TIKTOK-videonuoinick/<F>/avatar.jpg`

### Bước 5: Cập nhật Metadata & Đẩy Avatar lên thiết bị thật
- **Workbook:** Cập nhật `D:/OneDrive/TaadaaData/kibe/Tik<N>.xlsx`:
  - `video gốc`: `<F>`
  - `Folder Video`: `<F>`
  - `Keyword Video`: Tên Niche Hot chuẩn (ví dụ `Làm bánh ngọt`)
  - `Hashtag Pool`: Bộ hashtag tự nhiên của niche (ví dụ `#banhngot #lambanh #dessert #cake #anvat #sweet #xuhuong #fyp #videohay`)
  - `Video Đã Đăng`: Giữ nguyên số cũ
  - `Kiểm Tra Dữ Liệu`: `OK`
- **Database `state.db` (Bẫy 13 cột trong bảng `videos`):**
  - Cập nhật bảng `folders`: `status = 'complete'`, `video_count = N`, `source_channel = URL`, `niche = SLUG`.
  - Bảng `videos` có đúng **13 cột**:
    `(video_id, source_url, platform, niche, source_channel, uploader, view_count, language, language_score, status, folder, checked_at, output_path)`.
    Truyền thiếu cột sẽ ném `sqlite3.OperationalError: 12 values for 13 columns`.
- **Global Ledger:** Ghi nhận bản ghi `source_claimed` vào `D:/OneDrive/SharedData/tiktok-video/global-ledger/Kibe.jsonl`.
- **Hàng đợi & Runner:**
  - Cập nhật `avatar_replace_queue` trong `D:/Taadaa/data/tiktok_tracker.db` về `status = 'PENDING'`.
  - Khởi chạy runner chuyên dụng:
    `echo RUN | powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik <Tik> -MaxParallel 1 -HostConfigPath D:\Taadaa\machine-config\kibe.yaml -ForceAvatarMachineList "<May>"`
  - Khi runner hoàn tất, đọc `report.json` xác nhận `AVATAR_SMOKE_SUCCESS` và gửi ảnh composite đối chiếu qua `MEDIA:` cho Operator.
  - Cập nhật `avatar_replace_queue` về `status = 'DONE'`.

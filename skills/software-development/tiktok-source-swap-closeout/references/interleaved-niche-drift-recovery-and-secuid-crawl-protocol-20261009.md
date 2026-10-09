# Interleaved Niche Drift Recovery, sec_uid Crawl Bypass, and Three-Tier Dedup Protocol (2026-10-09)

## 1. Context & Symptom: Niche Drift & Avatar Mismatch on Farm Accounts
- **Triệu chứng**: Tài khoản TikTok farm (ví dụ `@yuethutiubk` M62 Tik 8) ban đầu đăng 5 clip bạn nữ Gen Z / daily vlog kéo view tốt (765 view, 11 followers), nhưng 3 clip gần nhất đột nhiên biến thành camera giao thông tai nạn xe cộ, view rớt thê thảm về đáy (48 view), và avatar bị cắt lẹm thành chữ vàng "hôi" từ banner cảnh báo tai nạn.
- **Nguyên nhân kép**:
  1. Thư mục `D:\video goc\496` bị tải đè kênh YouTube `@Cameragiaothong` trong đợt chuẩn hóa 640 folders ngày 11/09/2026.
  2. File điều phối `Tik8.xlsx` bị reset cột `Video Đã Đăng = 0` (hoặc lệch cursor), khiến runner bốc lại từ `1.mp4`, `2.mp4`, `3.mp4` của nguồn mới tải đè.
  3. Watchdog ca tối (`post_evening_avatar_watchdog.py`) tự động cắt frame từ `1.mp4` mới, trúng banner màu vàng có chữ "thôi", cắt lẹm thành chữ "hôi" và upload lên tài khoản.

## 2. Truy cứu Ground Truth & Giải thích cho Operator
- **Bẫy "Hệ thống có lưu DB không?"**:
  - `state.db` chuẩn của farm nằm tại `C:\CodexRuntime\tiktok-video\state.db` (34 MB) và `D:\CodexRuntime\tiktok-video\state.db` (23 MB), KHÔNG PHẢI các file 0-byte tại `D:\Taadaa\data\state.db` hay `D:\OneDrive\SharedData\tiktok-video\state.db`.
  - Các acc tạo từ cuối tháng 8/2026 được tải theo batch thủ công cũ trước khi đưa vào `state.db` tập trung. Đợt chuẩn hóa ngày 11/09 đã ghi đè metadata các folder từ 480..640 trong `state.db`. Do đó, metadata link nguồn của đợt tải cuối tháng 8 không còn trong DB offline.
- **Tư vấn dứt khoát: Đổi lại hay giữ nguyên?**:
  - Phải phân tích rõ cho Operator:
    * *Algorithm retention*: 5 clip đầu đã tạo footprint tệp khán giả trẻ. Khi đăng clip tai nạn giao thông, khán giả cũ lướt qua ngay (*swipe-away* cao), khiến TikTok ngắt phân phối ở vòng 1 (kẹt 48 view).
    * *Policy risk*: Clip va chạm/tai nạn đường phố có rủi ro cao dính vi phạm tiêu chuẩn cộng đồng về nội dung gây sốc/bạo lực.
    * *Kết luận*: BẮT BUỘC đổi lại ngách bạn nữ / vlog đời sống, dọn sạch video giao thông còn lại trong folder render.

## 3. TikTok sec_uid Playlist Crawl Bypass
- Khi cào video từ kênh TikTok bằng `yt-dlp "https://www.tiktok.com/@username"`, yt-dlp thường gặp lỗi:
  `Unable to extract secondary user ID. If you are able to get the channel_id from a video posted by this user, try using "tiktokuser:channel_id"`.
- **Giải pháp bóc tách `sec_uid` tức thì**:
  ```python
  import re, urllib.request, yt_dlp

  url = f"https://www.tiktok.com/@{username}"
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
  html = urllib.request.urlopen(req, timeout=5).read().decode("utf-8", errors="ignore")
  sec_uid = re.search(r'\"secUid\":\"([^\"]+)\"', html).group(1)

  # Truyền playlist qua sec_uid:
  pl_url = f"https://www.tiktok.com/@{sec_uid}"
  # yt-dlp nhận diện playlist trực tiếp và quét danh sách không lỗi
  ```
- **Lọc thời lượng chuẩn TikTok**:
  - Chỉ nhận các clip có `10.0 <= duration <= 65.0`.
  - Loại bỏ các clip quá ngắn (<10s) hoặc clip quá dài (>65s) để giữ tỷ lệ hoàn thành video cao khi bot đăng bài.

## 4. Quy trình đối soát chống trùng 3 tầng (Three-Tier Dedup)
Trước khi claim và cào một kênh creator mới cho bất kỳ folder nào, BẮT BUỘC đối soát đủ 3 tầng:
1. **Tầng 1 (Sổ cái Excel toàn farm)**: Quét toàn bộ các file `Tik1.xlsx` đến `Tik8.xlsx` của cả 2 trạm Kibe và Admin, cùng các workbook `taikhoan_dat_v2_updated.xlsx`. Đảm bảo không có dòng tài khoản nào đang dùng kênh này.
2. **Tầng 2 (Database & Claims)**: Kiểm tra `state.db` (`folders`, `videos`) và `data/gaixinh_channel_claims.json`. Xác nhận uploader chưa bị claim bởi folder khác.
3. **Tầng 3 (Global Ledger)**: Kiểm tra `D:\OneDrive\SharedData\tiktok-video\global-ledger\*.jsonl`. Phân biệt rõ giữa *claim nháp cũ không thực thi* (đã đổi sang niche khác) và *kênh đã tải thật*.

## 5. Xử lý xung đột Render Worker nền & Khóa cứng Workbook
- Nếu tiến trình `run_kibe_render_worker.py` đang chạy nền, nó quét các folder trong `Tik1..8.xlsx` có clip thành phẩm `< 45` để render.
- Nếu workbook có `video gốc` khác `Folder Video` (ví dụ `video gốc: 622`, `Folder Video: 496`), worker nền sẽ lấy video từ folder 622 render vào 496, gây khóa file `PermissionError: [WinError 32]` khi ta dọn dẹp hoặc render nguồn mới.
- **Trình tự xử lý**:
  1. Cập nhật ngay trong `Tik<N>.xlsx`:
     - `video gốc = Folder Video` (khóa 1:1, ví dụ cả 2 đều là `496`).
     - `Keyword Video`: Cập nhật đúng ngách mới (ví dụ `Đời sống`).
     - `Video Đã Đăng`: Ghi nhận đúng số clip đã có trên kênh (ví dụ `8`).
  2. Kill các tiến trình ffmpeg / random_batch_render đang render sai nguồn cũ.
  3. Để worker nền tự động nhận diện đúng nguồn mới và hoàn tất 45 clip thành phẩm chuẩn ngách.

## 6. Device Lock Coexistence & Upload Avatar Verification
- Khi thiết bị đang bận chạy ca bảo mật/2FA (`tiktok-add-bao-mat-f2a`), thiết bị có file lock `~/.codex/device-locks/machine_<N>.lock.json`.
- Runner upload avatar sẽ báo `SKIPPED_LOCKED`. TUYỆT ĐỐI CẤM tranh chấp lock hay kill tiến trình 2FA.
- Nạp bản ghi vào `avatar_replace_queue` với `status = 'PENDING'`.
- Khi máy nhả lock (kiểm tra `inspect_machine.py <N>` và không còn file lock), chạy runner với `-ForceAvatarMachineList "<M>"`.
- Nghiệm thu 3 lớp:
  * `summary.csv`: `ExitCode = 0`, `Status = THÀNH CÔNG`.
  * `report.json`: `status = AVATAR_SMOKE_SUCCESS`, `avatar_status = FORCED_REPLACED_VERIFIED`.
  * Visual evidence: Chụp ảnh màn hình qua `with_device_lock.py`, kiểm tra ảnh `avatar-uploaded-confirmed.png` bằng Vision API trước khi gửi thẻ `MEDIA:<path>` cho Operator.

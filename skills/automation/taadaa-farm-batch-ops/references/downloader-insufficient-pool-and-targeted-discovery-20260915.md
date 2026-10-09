# Triage Hiện Tượng Downloader Dừng Khi Thiếu Nguồn (Insufficient Pool), Xung Đột Global Ledger & Chiến Lược Targeted Discovery Phủ Kín 640 Folders

## 1. Bối Cảnh & Hiện Tượng (15/09/2026)
- Khi người vận hành hỏi: *"Clgt nãy h k render k down đc thêm gì cả"*, kiểm tra hiện trường phát hiện:
  - **Render**: Thực tế vẫn đang chạy bình thường (`run_kibe_slot7_slot8_render.ps1` điều phối 1 worker `ffmpeg`, encode liên tục folder 384 mỗi 10-14 phút/video).
  - **Downloader**: Tiến trình `download_by_niche.py` (PID 105020) sau khi chạy từ 06:49 đến ~17:50 đã hoàn tất lượt quét dải folder 481..640 và **tự động thoát**.
  - Đã có **542/640 folder** đạt $\ge 30$ video. Tuy nhiên còn **98 folder** (chủ yếu từ 600..640) bị dừng ở trạng thái `insufficient_pool`.

## 2. Nguyên Nhân Cốt Lõi Khiến 98 Folders Bị Insufficient Pool

### A. Cơ Chế Platform Ratio & Bẫy Cân Bằng Nửa Vời
- Trong `download_by_niche.py`:
  - `PLATFORMS = ("youtube", "tiktok")` và `PLATFORM_TARGET = {"youtube": 0.5, "tiktok": 0.5}`.
  - Hàm `choose_platform` tính tỷ lệ hoàn thành giữa các nền tảng: do YouTube đã hoàn thành 308 folder trong khi TikTok chỉ mới 61 folder, hệ thống liên tục gán `platform = 'tiktok'` cho các folder mới từ 600 trở đi (`ratio tiktok < ratio youtube`).
  - Trong khi đó, file pool chính `sources.qualified30.json` hiện tại **100% chỉ chứa nguồn YouTube Shorts**.
  - Hậu quả: Khi chọn `platform = 'tiktok'`, hàm `eligible_sources` không tìm thấy bất kỳ nguồn TikTok nào, ngay lập tức đánh dấu folder là `insufficient_pool` với `rejection_reason = "no_source_with_minimum_candidates"`.

### B. Cơ Chế Khóa Nguồn Toàn Cục (Global Ledger Claims)
- Hệ thống farm phân tán chia sẻ thư mục `D:/OneDrive/SharedData/tiktok-video/global-ledger`.
- Toàn bộ các kênh YouTube Shorts lớn trong pool (hơn 1.500 lượt claim) đã bị các máy Admin / Kibe chiếm quyền khai thác độc quyền (`claim_source` trong `download_by_niche.py` dòng 1450).
- Trong tổng số 506 kênh YouTube của `sources.qualified30.json`, chỉ còn **100 kênh chưa bị claim**, và các kênh này không phân bổ đều vào 48 niche còn thiếu của 98 folder (nhiều niche như `anh`, `laptrinh`, `nhay`, `chamsocbe`, `mevabe`, `dulich`, `mypham` có 0 kênh khả dụng).

## 3. Quy Chuẩn Xử Lý Kỹ Thuật (Targeted Discovery + Re-run)

### A. Bước 1: Targeted Discovery & Qualify Bổ Sung Vào sources.qualified30.json
- Thay vì chạy auto-discover toàn bộ 80 niches (dễ nghẽn và tốn thời gian), sử dụng kịch bản targeted:
  - Trích xuất danh sách các niche đang bị thiếu từ `C:/CodexRuntime/tiktok-video/state.db` (`WHERE status = 'insufficient_pool' AND folder_num >= 481`).
  - Dùng `scripts/fast_targeted_qualify_stream.py` với `ThreadPoolExecutor(max_workers=24)` xoay vòng qua `proxy_pool_67.txt`.
  - Probe trực tiếp tab `/shorts` của kênh ứng viên YouTube, chỉ chấp nhận các kênh có `shorts_count >= 30`.
  - Tự động nạp các kênh mới vào `D:/OneDrive/SharedData/tiktok-video/sources.qualified30.json`.

### B. Bước 2: Reset Folder Trong state.db & Khởi Chạy Downloader
- Reset các folder bị `insufficient_pool` về `pending`:
  ```sql
  UPDATE folders SET status = 'pending', platform = 'youtube' 
  WHERE folder_num >= 481 AND status = 'insufficient_pool';
  ```
- Khởi chạy downloader ngầm bằng lệnh chuẩn:
  ```bat
  "D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe" -u scripts/download_by_niche.py ^
    --total-folders 640 ^
    --start-folder 481 ^
    --sources "D:/OneDrive/SharedData/tiktok-video/sources.qualified30.json" ^
    --niche-pool "D:/Taadaa/Tiktok-video/data/niches_pool.txt" ^
    --exclusion-list "D:/Taadaa/Tiktok-video/data/exclusion_list.txt" ^
    --verified-channels "D:/Taadaa/Tiktok-video/data/verified_vn_channels.jsonl" ^
    --state-db "C:/CodexRuntime/tiktok-video/state.db" ^
    --runtime "C:/CodexRuntime/tiktok-video" ^
    --output-root "D:/video goc" ^
    --niche-mode strict ^
    --all-languages ^
    --min-videos 30 ^
    --target-videos 45 ^
    --max-videos 65 ^
    --max-folders-per-channel 2 ^
    --parallel 20 ^
    --continue-on-insufficient ^
    --proxy-pool "D:/Taadaa/Tiktok-video/proxy_pool_67.txt" ^
    --cookies-dir "D:/CodexRuntime/tiktok-video" ^
    --global-ledger-dir "D:/OneDrive/SharedData/tiktok-video/global-ledger" ^
    --ledger-machine-id Kibe
  ```
- Đảm bảo giữ nguyên tiến trình render (`run_kibe_slot7_slot8_render.ps1` / `ffmpeg.exe`), tuyệt đối không can thiệp hay kill nhầm.

## 4. Pitfall Khi Chạy Focused / Canary Test 1 Folder (start-folder == total-folders)
- **Kẹt platform cũ trong state.db:** Khi chạy canary test cho 1 folder cụ thể (ví dụ `--start-folder 601 --total-folders 601`), nếu folder đó đã có record cũ trong `state.db` với `platform='tiktok'` (hoặc platform khác), `download_by_niche.py` sẽ tự động đọc `folder_row["platform"]` từ DB và cố tìm nguồn TikTok.
- **Hiện tượng:** Trong khi file nguồn `--sources` chỉ chứa 100% kênh YouTube, downloader sẽ ngay lập tức trả về `INSUFFICIENT_POOL folder=601 ... platform=tiktok ... sources_checked=1 required=30` và kết thúc exit code 0 mà không tải bất kỳ video nào.
- **Khắc phục chuẩn khi Canary test:**
  1. Thêm cờ ép platform: `--fixed-platform youtube` (hoặc `--fixed-niche <slug>` nếu muốn test đích danh niche).
  2. Hoặc reset sạch bản ghi folder trong `state.db` trước khi chạy:
     ```sql
     UPDATE folders SET status='pending', platform='youtube', source_channel=NULL, video_count=0 WHERE folder_num=601;
     ```


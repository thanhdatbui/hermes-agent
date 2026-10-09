# Khắc phục & Điều phối Download Niche Hot và Render Đơn Luồng (Kibe & Admin)

## 1. Bối cảnh & Mục tiêu
Khi vận hành cào video gốc (Shorts/TikTok) và render video nuôi nick trên 2 cụm Kibe (Máy 1-80) và Admin (Máy 201-280):
- **Tiêu chuẩn video gốc**: Tối thiểu >= 45 clip (target 45–65 clip), 100% đúng ngách (12 Niche Hot hoặc pool chuẩn 80 niche), kèm avatar (`channel_avatar.jpg`).
- **Kỷ luật Render**: Bắt buộc **1 worker đơn luồng (`--parallel 1`)** trên cả 2 máy theo lệnh vận hành, tránh quá tải CPU/RAM hoặc lỗi ffmpeg.
- **Chống trùng nguồn**: Sử dụng `global-ledger` trên OneDrive (`D:\OneDrive\SharedData\tiktok-video\global-ledger`) với mã định danh máy (`--ledger-machine-id Kibe` / `--ledger-machine-id Admin`).

---

## 2. Các cạm bẫy & Xử lý lỗi hệ thống (Root Causes & Fixes)

### 🔴 Cạm bẫy 1: Windows Pagefile OOM (`WinError 1455`, Exit 139)
- **Hiện tượng**: Chạy download đa luồng quá cao (`--parallel 20` trở lên) kết hợp tải yt-dlp, xử lý âm thanh/OpenCV/Whisper khiến Windows cạn kiệt paging file và crash tiến trình ngầm đột ngột.
- **Giải pháp**:
  - Khóa trần download an toàn ở mức **`--parallel 10`** trên máy Windows.

### 🔴 Cạm bẫy 2: Xung đột SQLite Disk I/O trên file `state.db`
- **Hiện tượng**: Nhiều worker download/render cùng kết nối vào `C:\CodexRuntime\tiktok-video\state.db` hoặc `D:\CodexRuntime\tiktok-video-machine2\state.db` gây lỗi `sqlite3.OperationalError: disk I/O error` hoặc `database is locked`.
- **Giải pháp**:
  - Bọc hàm `connect_state()` trong `pipeline_common.py` với retry 5 lần, sleep backoff 0.5s và thiết lập `timeout=30.0`.
  - Thiết lập `PRAGMA journal_mode=WAL;` và `PRAGMA busy_timeout=30000;` an toàn.

### 🔴 Cạm bẫy 3: Lỗi Import & Môi trường Python trên Remote Admin qua SSH
- **Hiện tượng**:
  1. Gọi `python` mặc định trên Admin có thể trỏ vào venv không có `cv2` hoặc `yt-dlp` (`No module named 'cv2'`).
  2. Lỗi `ValueError: niches_pool phai co 80 niche, hien co 87` do file `niches_pool.txt` trên máy Admin chưa đồng bộ bản chuẩn với Kibe.
  3. Lỗi relative import khi chạy script độc lập (`attempted relative import with no known parent package`).
- **Giải pháp**:
  - Trên Admin, sử dụng đúng Python venv đầy đủ dependency: `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe`.
  - Đồng bộ `pipeline_common.py`, `download_by_niche.py`, và `data/niches_pool.txt` từ Kibe sang Admin qua `scp` trước khi chạy.
  - Chạy background script thông qua wrapper foreground loop hoặc Scheduled Task để tiến trình không bị kill khi phiên SSH đóng.

### 🔴 Cạm bẫy 4: Lỗi Windows File Lock khi dọn file tạm (`PermissionError: [WinError 32]`)
- **Hiện tượng**: Trong quá trình cào khi một kênh không đủ clip, tiến trình dọn dẹp các file `.part`, `.mp4`, `.jpg` dở dang bị crash do Windows lock handle.
- **Giải pháp**:
  - Bọc khối `try...except OSError` kèm retry 3 lần có `time.sleep(0.5)` khi `fpath.unlink()`.

---

## 3. Lệnh chuẩn khởi chạy (Canonical Commands)

### A. Download cào nguồn Niche Hot trên Kibe (10 Worker):
```bash
"D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe" -u "D:\Taadaa\Tiktok-video\scripts\download_by_niche.py" \
  --total-folders 640 \
  --sources "D:\OneDrive\SharedData\tiktok-video\sources.qualified30.json" \
  --niche-pool "D:\Taadaa\Tiktok-video\data\niches_pool.txt" \
  --exclusion-list "D:\Taadaa\Tiktok-video\data\exclusion_list.txt" \
  --verified-channels "D:\Taadaa\Tiktok-video\data\verified_vn_channels.jsonl" \
  --state-db "C:\CodexRuntime\tiktok-video\state.db" \
  --runtime "C:\CodexRuntime\tiktok-video" \
  --output-root "D:\video goc" \
  --niche-mode strict \
  --min-videos 45 \
  --target-videos 45 \
  --max-videos 65 \
  --max-folders-per-channel 2 \
  --parallel 10 \
  --continue-on-insufficient \
  --all-languages \
  --proxy-pool "D:\Taadaa\Tiktok-video\proxy_pool_67_direct.txt" \
  --global-ledger-dir "D:\OneDrive\SharedData\tiktok-video\global-ledger" \
  --ledger-machine-id Kibe
```

### B. Download cào nguồn Niche Hot trên Admin (10 Worker via SSH):
```bash
ssh admin-farm "D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe -u D:\Taadaa\Tiktok-video\scripts\download_by_niche.py \
  --total-folders 640 \
  --sources D:\OneDrive\SharedData\tiktok-video\sources.qualified30.json \
  --niche-pool D:\Taadaa\Tiktok-video\data\niches_pool.txt \
  --exclusion-list D:\Taadaa\Tiktok-video\data\exclusion_list.txt \
  --verified-channels D:\Taadaa\Tiktok-video\data\verified_vn_channels.jsonl \
  --state-db D:\CodexRuntime\tiktok-video-machine2\state.db \
  --runtime D:\CodexRuntime\tiktok-video-machine2 \
  --output-root \"D:\video goc may 2\" \
  --niche-mode strict \
  --min-videos 45 \
  --target-videos 45 \
  --max-videos 65 \
  --max-folders-per-channel 2 \
  --parallel 10 \
  --continue-on-insufficient \
  --all-languages \
  --proxy-pool D:\Taadaa\Tiktok-video\proxy_pool_67_direct.txt \
  --global-ledger-dir D:\OneDrive\SharedData\tiktok-video\global-ledger \
  --ledger-machine-id Admin"
```

### C. Render nối tiếp 1 Worker (`--parallel 1`):
- Luôn truyền cờ `--parallel 1` và `--resume-verify-existing` để kiểm tra độ nguyên vẹn qua `ffprobe` trước khi quyết định render bù hoặc bỏ qua các clip đã hoàn thành tốt.

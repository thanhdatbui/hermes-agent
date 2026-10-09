# Download Relaunch Checklist — Kibe 640 folders (2026-09-13)

## 1. Tik workbook → video gốc mapping (xác minh bằng pandas trên Tik1..Tik8.xlsx)
- Tik1: Folder Video `1,9,17...633` (slot 1), video gốc `1..80`
- Tik2: Folder Video `2,10,18...634` (slot 2), video gốc `81..160`
- Tik3: `3..635`, gốc `161..240` | Tik4: `4..636`, gốc `241..320`
- Tik5: `5..637`, gốc `321..400` | Tik6: `6..638`, gốc `401..480`
- Tik7: `7..639`, gốc `481..560` | Tik8: `8..640`, gốc `561..640`
- Công thức kiểm tra nguồn theo state.db cho slot N (Kibe m=1..80):
  `folder_num = (m-1)*8 + slot`. Đừng nhầm với Folder Video render (cùng số nhưng nằm ở `D:\TIKTOK-videonuoinick`).

## 2. Preflight trước khi chạy download lại
1. Xác định DB chuẩn: `C:\CodexRuntime\tiktok-video\state.db` (SSD, mới nhất) vs `D:\CodexRuntime\...` (cũ). So sánh `count(*)` 2 bên, chạy trên bản C:.
2. Kiểm tra tiến trình thật: `Get-CimInstance Win32_Process` lọc `download_by_niche` (wmic qua git-bash bị bọc bash noise — dùng powershell.exe trực tiếp).
3. Reset folder kẹt: `UPDATE folders SET status='pending', platform='youtube', source_channel=NULL, video_count=0 WHERE status='insufficient_pool'`. Chỉ reset status là KHÔNG đủ (platform cũ giữ lại sẽ fail lại).
4. Verify file tồn tại: `proxy_pool_67.txt`, `sources.qualified30.json`, cookies-dir, output-root `D:\video goc`.

## 3. Lệnh canonical (Kibe, 481..640)
- Python BẮT BUỘC: `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe` (không dùng python mặc định của Hermes venv).
- CWD BẮT BUỘC: `D:\Taadaa\Tiktok-video` vì `download_by_niche.py` mặc định đọc `data/niches_pool.txt` tương đối. Hoặc truyền tuyệt đối `--niche-pool/--exclusion-list/--verified-channels`.
- Flags: `--total-folders 640 --start-folder 481 --min-videos 30 --target-videos 45 --max-videos 65 --max-folders-per-channel 2 --parallel 20 --continue-on-insufficient --proxy-pool proxy_pool_67.txt --cookies-dir C:/CodexRuntime/tiktok-video --global-ledger-dir ... --ledger-machine-id Kibe`.
- Download là Network I/O → `--parallel 20` an toàn với pool 67 proxy. Render mới giữ `--parallel 1`.

## 4. Cách launch qua Hermes terminal (tránh double-process)
- CẤM chạy `.bat` trực tiếp trong terminal background (đã gây 2 python.exe cùng cmdline: 1 từ venv-core024 + 1 từ uv python 3.11).
- Pattern chuẩn: ghi `run_download_kibe.py` dùng `subprocess.Popen(cmd, stdout=log, stderr=STDOUT, cwd=repo_dir)` rồi `python run_download_kibe.py` (foreground, trả về PID ngay). Log ghi vào `D:\CodexRuntime\tiktok-video\download_run.log`.
- Verify sau launch: `Get-Process -Id <pid>` Responding=True + `Get-CimInstance Win32_Process -Filter "ParentProcessId = <pid>"` thấy 1 child + `is_download_running()==True`.

## 5. Watchdog perf (đo thực tế 13/09)
- `is_download_running()` qua psutil mất ~22s trên host Kibe — đừng gọi lặp dày.
- `get_source_video_stats()` từ state.db ~0.00s (ưu tiên DB, cấm scan đĩa).
- `get_render_stats()` slot 1-4 ~0.02s/slot nhưng slot 5-8 mất 5-48s/slot khi ổ HDD bận → watchdog toàn farm có thể >180s timeout khi download đang chạy. Khi cần số liệu nhanh, đo từng slot hoặc chỉ đọc state.db.

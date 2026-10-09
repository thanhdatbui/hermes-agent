# Quy trình Chẩn đoán O(1) khi Downloader Tự Dừng (Trạng thái download: ⚪ Đang dừng)

## 1. Triệu chứng & Bản chất
- **Triệu chứng**: Watchdog `farm-render-download-watchdog` báo `Trạng thái download: ⚪ Đang dừng`. Người dùng thắc mắc *"Sao dừng download r"*, *"Sao không tải nữa"*.
- **Bản chất**: Tiến trình `download_by_niche.py` chạy tuần tự hoặc song song qua dải folder (1..640). Khi hoàn thành folder cuối cùng (folder 640), script in log `COMPLETE folder=640 ... -> DONE` và kết thúc tiến trình một cách tự nhiên. **Đây là hoàn tất vòng quét (normal exit), KHÔNG PHẢI lỗi crash, đơ treo hay out-of-memory.**

---

## 2. Các bước chẩn đoán O(1) cho Coordinator (Tuyệt đối cấm scan đĩa diện rộng)

### Bước 1: Tra cứu nhanh SQLite `state.db` (< 10ms)
Đường dẫn ưu tiên: `C:\CodexRuntime\tiktok-video\state.db` (fallback `D:\CodexRuntime\tiktok-video\state.db`).
Chạy truy vấn O(1):
```python
import sqlite3
conn = sqlite3.connect(r'C:\CodexRuntime\tiktok-video\state.db')
cur = conn.cursor()

# 1. Tổng quan số lượng
cur.execute('''
    SELECT count(*), 
           sum(case when video_count >= 30 then 1 else 0 end) as ge30,
           sum(case when video_count >= 45 then 1 else 0 end) as ge45,
           sum(video_count) as total_vids
    FROM folders
''')
print("Stats:", cur.fetchone())

# 2. Tìm folder chưa đạt chuẩn >= 30
cur.execute('SELECT folder_num, niche, video_count, status, source_channel FROM folders WHERE video_count < 30')
under30 = cur.fetchall()
print("Under 30 folders:", under30)

# 3. Lấy 5 folder hoàn thành gần nhất
cur.execute('SELECT folder_num, completed_at FROM folders ORDER BY completed_at DESC LIMIT 5')
print("Latest completed:", cur.fetchall())
conn.close()
```
- Nếu `Latest completed` chứa folder 640 với timestamp mới nhất -> Khẳng định chắc chắn batch đã chạy trọn vẹn dải 1..640.

### Bước 2: Đọc đuôi Log & Report JSONL
- **Log run**: `tail -n 25 /d/CodexRuntime/tiktok-video/download_run.log`
  - Tìm dòng kết thúc: `COMPLETE folder=640 videos=... avatar=True` theo sau bởi `DONE report=...`.
- **Report JSONL**: Đọc 20 dòng cuối của file `report-YYYYMMDD-HHMMSS.jsonl` mới nhất trong `C:\CodexRuntime\tiktok-video\`.

---

## 3. Cơ chế Bảo toàn Invariant: `clean_incomplete_folder_and_db`
Khi kiểm tra thấy folder bị `insufficient_pool` và thư mục `D:\video goc\<folder>` trống trơn:
- **Nguyên nhân**: Khi Auto-Discovery quét kênh Shorts của niche đó nhưng các video Shorts bị lỗi stream (`download_no_media`, lỗi ffmpeg map `Stream map '' matches no streams`), hoặc kênh không có đủ 30 video đạt chuẩn ngôn ngữ.
- **Invariant Farm**: Nhằm tránh tình trạng **1 folder trộn 2 kênh video khác nhau**, script kích hoạt `clean_incomplete_folder_and_db`:
  1. Xóa sạch file media dở dang (`.mp4`, `.part`, `.jpg`) trong folder đó.
  2. Xóa sạch bản ghi video dở dang trong SQLite `videos`.
  3. Đánh dấu folder status = `insufficient_pool`, `source_channel = NULL`.
  4. Script tiếp tục hành trình đến folder tiếp theo, không làm kẹt tiến trình batch.

---

## 4. Mẫu phản hồi chuẩn cho người dùng (ACTION-FIRST, TUYỆT ĐỐI CẤM DỪNG HỎI)
- **CẤM TUYỆT ĐỐI**: Không bao giờ dừng tiến trình rồi hỏi *"Sếp có muốn chạy bù/vét tiếp không"*. Đây là lỗi vi phạm nguyên tắc Action-First, đẩy việc quyết định sang người dùng.
- **Quy tắc phản hồi**:
  1. **Khẳng định ngay**: Tiến trình không bị crash/treo, đã quét xong 1 lượt toàn bộ dải 640 folder và hoàn tất tự nhiên lúc [HH:MM].
  2. **Số liệu cụ thể**:
     - Tổng video MP4: [N] video.
     - Số folder đạt chuẩn $\ge 30$: [X] / 640 folder ([Y]%).
     - Số folder complete ($\ge 60$): [A] folder.
  3. **Giải thích folder còn thiếu (nếu có)**: Chỉ rõ folder số mấy, ngách gì, nguyên nhân chưa đạt (e.g. video kênh auto-discovered bị lỗi stream/ffmpeg, hệ thống đã dọn sạch để bảo vệ invariant 1 folder = 1 kênh duy nhất).
  4. **Hành động tức thì (Action-First)**: Thông báo rằng hệ thống **đã tự động kích hoạt tiến trình cào vét tuần hoàn (`scripts/auto_rescan_loop.py`)** để tự động tìm nguồn mới và kéo tiếp cho đến khi đạt 100%, không để farm đứng chờ.

---

## 5. Kỷ luật Vòng lặp Tuần hoàn (Autonomous Re-Scan Loop)
- **Bản chất của `download_by_niche.py`**: Vòng lặp chính là single-pass qua danh sách folder (`for folder_num in folder_list:`). Khi chạy đến folder cuối cùng, script in `DONE` và `sys.exit(0)`.
- **Bắt buộc có tầng Giám sát Tuần hoàn (Runner Loop - `scripts/auto_rescan_loop.py`)**:
  - Để tránh việc downloader dừng khi vẫn còn folder chưa đạt $\ge 30$ video, launcher nền (`scripts/auto_rescan_loop.py`) phải liên tục:
    1. Query `state.db`: `SELECT folder_num FROM folders WHERE video_count < 30 OR status = 'insufficient_pool'`.
    2. Nếu rỗng: Log `ALL_FOLDERS_COMPLETE: 640/640 folders have >= 30 videos` và dừng an toàn với exit code `0`.
    3. Nếu còn folder thiếu: Spawn `download_by_niche.py --folders <danh_sach_thieu>` kèm Auto-Discovery, ghi log append vào `download_run.log`.
    4. **Fail-safe & Backoff**: Khi subprocess gặp lỗi (`returncode != 0`), tự động tăng `consecutive_failures` và áp dụng exponential backoff (`interval * 2^(failures-1)`). Nếu chạm ngưỡng `max_consecutive_failures` (mặc định 5), script tự động ngắt an toàn và cảnh báo để bảo vệ tài nguyên farm.
    5. **Structured Telemetry & Status File**: Xuất atomic file `rescan_status.json` chứa tiến độ (`complete`, `total`, `pct`, `incomplete_folders`) và ghi log metrics rõ ràng:
       `AUTONOMOUS_RESCAN_ROUND_METRICS round=N duration_s=X exit_code=Y folders_before=A folders_after=B folders_repaired=C`
    6. Chờ lượt quét xong, sleep interval (15-20s) rồi lặp lại bước 1.
  - **Unit Test Suite (`tests/test_auto_rescan_loop.py`)**: Đầy đủ 8 tests kiểm thử focused (< 0.5s): query SQLite, progress summary, command builder, override custom path, complete exit, max rounds, consecutive failures backoff, và status JSON validation.
  - Tuyệt đối không để tiến trình dừng im và yêu cầu người dùng phải tự tay chạy lệnh vét.

---

## 6. Lệnh Khởi chạy Chuẩn hóa (Canonical Entrypoints)
- **Khởi chạy Downloader Farm tuần hoàn (Auto-Rescan Loop)**:
  ```bash
  /d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe D:/Taadaa/Tiktok-video/run_download_kibe.py
  ```
  Script này sẽ spawn `scripts/auto_rescan_loop.py` chạy ngầm (background process group), log ghi liên tục vào `D:\CodexRuntime\tiktok-video\download_run.log`.
- **Giám sát trạng thái Watchdog**:
  Watchdog `farm_render_download_watchdog.py` tự động phát hiện cả `auto_rescan_loop.py` và `download_by_niche.py` để báo `🟢 Đang chạy`.

---

## 7. Quy trình Chẩn đoán O(1) khi Render Dừng & Thiết lập Watchdog Báo cáo Farm Alert

### A. Bản chất khi Render dừng (⚪ Đang dừng)
- **Kiểm tra tiến trình active**:
  `wmic process where "name='python.exe' or name='ffmpeg.exe'" get commandline` (tìm `random_batch_render.py`, `run_render`, `ffmpeg`).
- **Xác định nguyên nhân dừng**:
  - Không có tiến trình chạy ngầm nghĩa là **batch render trước đó đã chạy xong toàn bộ danh sách queue được giao và kết thúc tự nhiên (normal exit)**, không phải treo crash.
  - Chạy `python C:/Users/Kibe/AppData/Local/hermes/scripts/farm_render_download_watchdog.py` để lấy nhanh thống kê 8 slot Tik1..Tik8.
  - Nếu các slot đạt 80/80 (hoặc các folder còn thiếu nằm trong danh sách đang đổi nguồn / chờ nạp nguồn mới như Tik4 Máy 47, Tik7 nhóm gái xinh) -> Xác nhận queue đã render hết tài nguyên sẵn sàng.

### B. Cấu hình Watchdog Báo cáo Farm Alert định kỳ 6h
- **Watchdog job**: `farm-render-download-watchdog` (chạy script `farm_render_download_watchdog.py`).
- **Đích gửi (Destination)**: Cấu hình `deliver='telegram:-5373649734'` để gửi về nhóm Farm Alert thay vì chat riêng (`origin`).
- **Lịch báo cáo**: `0 */6 * * *` (mỗi 6 tiếng một lần: 00:00, 06:00, 12:00, 18:00).
- **Quy tắc Ẩn phần Download khi Hoàn tất 100% ("Download xong thì không báo nữa")**:
  - Khi kho video gốc toàn cụm đã đạt 100% ($\ge 30$ video cho cả 640/640 folder) và tiến trình downloader không chạy, watchdog `farm_render_download_watchdog.py` BẮT BUỘC **tự động ẩn mục 1 (Video gốc)**, chỉ hiển thị tập trung **Tiến độ Render Tik1..Tik8**.
  - Tiêu đề rút gọn: `📊 BÁO CÁO TIẾN ĐỘ FARM KIBE (RENDER)`.
- **Quy tắc đồng bộ tức thì (Mandatory Sync Rule)**:
  Mỗi khi thay đổi schedule/destination của cronjob trong Hermes, BẮT BUỘC chạy ngay:
  ```bash
  python C:/Users/Kibe/AppData/Local/hermes/scripts/cron_sync_watchdog.py
  ```
  để đồng bộ tức thì `jobs.json` sang Git Deploy (`D:\Taadaa\Hermes\deploy\hermes-home\cron\jobs.json`) và OneDrive Shared (`D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\jobs.json`), tránh tình trạng chờ 15 phút mới sync.

---

## 8. Điều phối Remote Batch Ops Cụm Admin (Máy 201..280) qua SSH
Xem chi tiết tại: `references/admin-cluster-remote-batch-ops.md`.
- **Chuỗi Render cuốn chiếu Admin (`admin_render_chain.py`)**:
  ```bash
  ssh admin-farm 'powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath python -ArgumentList @(\"D:/Taadaa/Tiktok-video/scripts/admin_render_chain.py\", \"--start-from\", \"5\", \"--skip-wait-tik2\") -WorkingDirectory \"D:/Taadaa/Tiktok-video\" -WindowStyle Hidden"'
  ```
- **Pipeline cào video Gái xinh VN + Douyin trên Admin (`run_admin_gaixinh_downloader.py`)**:
  - Lưu tại `D:\video goc may 2`.
  - Tự động bắt bẫy mã hóa Unicode với `PYTHONIOENCODING=utf-8` và reconfigure stdout/stderr tránh crash `cp1252`.

---

## 9. Chẩn đoán 2 Nút thắt khi Downloader Dừng Ngang & Tự Thoát (Cạn Kênh Manifest & Ổ Đĩa Đầy 0-byte Free)
- **Hiện tượng**: User chất vấn gay gắt: *"Trc đó t yêu cầu down tiếp cho đủ r sao cứ dừng đéo làm v"*, watchdog ca nuôi nick báo nhiều máy dính `Hết video/Cần cào`.
- **Nút thắt 1: Cạn kênh trong Manifest tĩnh (Static Manifest Exhaustion)**:
  - Downloader đơn luồng duyệt qua file manifest tĩnh (ví dụ `source_manifest_admin_vn.jsonl` có 576 kênh). Khi đã cấp sổ cái (`claims`) cho toàn bộ kênh sống trong manifest, vòng lặp gán kênh `while valid_count < 35 and channel_idx < len(channels)` tự kết thúc.
  - Script in log `=== HOÀN TẤT TOÀN BỘ QUY TRÌNH DOWNLOAD ===` và exit 0 tự nhiên dù vẫn còn hàng chục folder đang có 0 clip.
  - **Khắc phục**: Tuyệt đối không để farm dừng im. Khi hết manifest tĩnh, bắt buộc tự động fallback sang cơ chế tìm kiếm động theo từ khóa YouTube Shorts có cookie (`youtube-cookies.txt`) hoặc nạp thêm manifest mới.
- **Nút thắt 2: Ổ đĩa bị đầy 100% (Free: 0 GB / 0 bytes)**:
  - Trên Windows host/Admin, khi ổ `D:` còn 0 byte free (`Get-Volume -DriveLetter D | Select SizeRemaining`), `yt-dlp` và `ffmpeg` sẽ thất bại âm thầm hoặc không thể ghi file tạm `.part` / `.mp4`.
  - **Quy trình thu hồi dung lượng O(1) an toàn (Safe Purge of Rendered Sources)**:
    - Đối soát giữa folder video gốc (`D:\video goc may 2\<folder>`) và folder render thành phẩm (`D:\TIKTOK-videonuoinick-admin\<folder>`).
    - **Quy tắc thu hồi**: Bất kỳ folder nào mà thư mục render tương ứng ĐÃ HOÀN THÀNH ĐỦ $\ge 45$ clip thành phẩm (`(Get-ChildItem $renderDir -Filter *.mp4).Count -ge 45`), thì toàn bộ video gốc trong `video goc may 2\<folder>` được phép dọn sạch an toàn để giải phóng ổ cứng (mỗi folder thu hồi ~100–150 MB, 500 folder thu hồi ~50–60 GB).
    - Lệnh PowerShell kiểm tra & thu hồi dung lượng O(1):
      ```powershell
      # 1. Kiểm tra số folder và dung lượng có thể giải phóng
      $clean_b = 0; $clean_f = 0
      foreach ($d in (Get-ChildItem 'D:\video goc may 2' -Directory)) {
          $rd = Join-Path 'D:\TIKTOK-videonuoinick-admin' $d.Name
          if (Test-Path $rd) {
              $cnt = (Get-ChildItem $rd -Filter *.mp4 -ErrorAction SilentlyContinue).Count
              if ($cnt -ge 45) {
                  $sz = (Get-ChildItem $d.FullName -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
                  if ($sz -gt 0) { $clean_f++; $clean_b += $sz }
              }
          }
      }
      Write-Host "Có thể dọn $clean_f folders, giải phóng $([math]::Round($clean_b / 1GB, 2)) GB"

      # 2. Xóa an toàn các file gốc của các folder đã render >= 45 clips
      foreach ($d in (Get-ChildItem 'D:\video goc may 2' -Directory)) {
          $rd = Join-Path 'D:\TIKTOK-videonuoinick-admin' $d.Name
          if (Test-Path $rd) {
              $cnt = (Get-ChildItem $rd -Filter *.mp4 -ErrorAction SilentlyContinue).Count
              if ($cnt -ge 45) {
                  Get-ChildItem $d.FullName -File -ErrorAction SilentlyContinue | Remove-Item -Force
              }
          }
      }
      ```
- **Kỷ luật phản hồi User**:
  - Không nói chung chung "đang kiểm tra" hay "tiến trình đang chạy".
  - Nêu rõ 3 điểm hiện trường cụ thể: (1) Dung lượng ổ đĩa còn lại (Free GB / SizeRemaining), (2) Trạng thái tiến trình & nguyên nhân script cũ tự thoát (hết manifest hay crash), (3) Số folder đã render $\ge 45$ clip có thể dọn nguồn để lấy ngay hàng chục GB trống.

- **Nút thắt 3: File Cookie Bị Truncate 0-Byte Khi Đĩa Tràn (0-Byte Cookie Cascading Failure)**:
- **Triệu chứng**: Khi ổ đĩa D: chạm 0 byte free, các thao tác ghi file tạm có thể làm file `youtube-cookies.txt` bị truncate thành 0 byte (`Length = 0`). Khi đó `yt-dlp` không báo lỗi bot-check hay timeout mạng mà văng lỗi:
  `ERROR: '...youtube-cookies.txt' does not look like a Netscape format cookies file`
- **Hệ quả dây chuyền**: Mỗi kênh thử tải đều thất bại sau ~1 giây (`valid_count = 0`), khiến script duyệt cạn toàn bộ hàng trăm kênh khả dụng trong vài phút và kết thúc tự nhiên (`exit 0`), để lại hàng chục folder trống.
- **Khắc phục**:
  1. Kiểm tra kích thước cookie: `Get-Item D:\CodexRuntime\tiktok-video\youtube-cookies.txt | Select Length`.
  2. Nếu `Length == 0`, lập tức SCP khôi phục file Netscape cookie chuẩn từ Kibe sang Admin:
     `scp D:/CodexRuntime/tiktok-video/youtube-cookies.txt admin-farm:D:/CodexRuntime/tiktok-video/youtube-cookies.txt`
- **Bảo toàn Invariant Chống Trộn Kênh (`Anti-Mixing Invariant`)**:
  Trong `run_admin_clean_vn_downloader.py`, nếu kênh đang tải có `< 35` video, trước khi thử kênh tiếp theo BẮT BUỘC phải dọn sạch các file `.mp4`, `.part`, `.jpg` dở dang trong folder để tránh gộp video của 2 kênh khác nhau vào cùng 1 folder.
- **Đồng bộ Watchdog Bắt Đúng Downloader**:
  Hàm `is_download_running()` trong `farm_render_download_watchdog.py` bắt buộc phải kiểm tra thêm các pattern `clean_vn`, `run_admin_clean_vn`, `run_admin_downloader` bên cạnh `download_by_niche.py` để watchdog hiển thị chính xác trạng thái `🟢 Đang chạy`.

- **Nút thắt 4: Bẫy `fallback_niches` Chéo Ngách & Kỷ Luật Khóa Chết Đúng Niche 100%**:
- **Sự cố thực tế**: Người dùng bức xúc gay gắt vì script tự tiện tải video lệch chủ đề (gán kênh bóng đá vào niche *Làm đẹp*, kênh tin tức vào *Thiết bị*, kênh phim vào *Tâm lý*).
- **Căn nguyên**: Đoạn mã `fallback_niches` cũ trong `download_by_niche.py` tự ý đổi `niche = fb_niche` sang *Hài hước, Tin tức, Ẩm thực...* khi thiếu nguồn, và `sources.master_1288.json` bị tag bừa bãi đài truyền hình (VTV, HTV, THVL) vào các ngách hẹp.
- **Kỷ luật cốt lõi (Hard Invariants)**:
  1. *CẤM TUYỆT ĐỐI FALLBACK KHÁC NICHE*: Folder ngách nào khóa chết 100% ngách đó. Thiếu nguồn thì tiếp tục cào thêm nguồn CÙNG NICHE; nếu cạn nguồn thì dừng báo thiếu, tuyệt đối không tráo sang ngách khác.
  2. *Targeted Query Search*: Tìm kiếm trực tiếp YouTube Shorts bằng từ khóa chuyên sâu của đúng niche (`ytsearch15:{niche_label} shorts việt nam`, `ytsearch15:chia sẻ {niche_label} shorts`, `ytsearch15:#{niche_slug} shorts việt nam`).
  3. *Blacklist đài truyền hình & tin tức*: Lọc bỏ triệt để kênh chứa `vtv`, `htv`, `thvl`, `báo`, `tin tức`, `truyền hình`, `bóng đá`, `tổng hợp`...
  4. *Probe Gate $\ge 40$ clips*: Kiểm tra nhanh tab `/shorts` trước khi tải; kênh $< 35$ clips bỏ qua ngay trong 2s, chỉ tải kênh $\ge 40$ clips.
  5. Xem chi tiết hướng dẫn và quy chuẩn tại: `references/strict-same-niche-crawling-and-anti-cross-niche-fallback.md`.

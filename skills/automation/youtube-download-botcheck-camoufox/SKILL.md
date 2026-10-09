---

name: youtube-download-botcheck-camoufox

description: Fix yt-dlp bị YouTube bot-check ("Sign in to confirm you're not a bot" / HTTP 403 / NA) khi tải video — dùng Camoufox lấy cookies phiên thật. Áp dụng cho download_by_niche.py (Tiktok-video farm) và mọi tải YouTube.

---



# YouTube download qua bot-check (Camoufox cookies)


## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

## Trigger

yt-dlp trả "Sign in to confirm you're not a bot", HTTP 403 rải rác, hoặc "NA" khi probe/tải YouTube.



## Root cause

YouTube chặn theo dấu hiệu **CLIENT** (thiếu browser fingerprint thật + không giải được JS challenge), không chỉ IP. Proxy di động đổi IP KHÔNG hết; chỉ cookies phiên / browser thật mới qua được.



## Fix: Camoufox cookies (đã kiểm chứng 17/08/2026)

1. Cài: `python -m pip install "camoufox[geoip]"` + `python -m camoufox fetch` (venv-core024 đã có sẵn)

2. Mở `https://www.youtube.com` headless bằng Camoufox (script mẫu: `D:\CodexRuntime\tiktok-video\test-camoufox-cookies-20260816.py`) → export cookies Netscape → `youtube-cookies-netscape.txt`

3. yt-dlp chạy với `--cookies-file <file>` → qua bot-check (test: video Numb OK, channel flat OK)

4. **Cookies hết hạn ~vài giờ** → refresh lại bằng Camoufox khi download bắt đầu "Sign in" trở lại



## Tích hợp download_by_niche.py

- Flag `--cookies-file <path>` → `options["cookies"]`

- Flag `--proxy-pool <xlsx>` → xoay proxy mỗi video (format `host:port:user:pass` từ PROXYgandienthoai.xlsx → `http://user@host:port`; 76 proxy, ~số lớn active)

- Flag `--continue-on-insufficient` → skip folder thiếu nguồn, không dừng batch

- **1 folder = 1 kênh DUY NHẤT** (bất biến — user cấm trộn kênh): `run_folder` break ngay khi source đầu tiên đủ min-videos; parallel chỉ tải song song video CÙNG kênh trong folder đó

### Worker isolation & Scale (song song nhiều folder/kênh) — 17-18/08/2026
Mỗi worker = 1 subpool proxy riêng (không trùng IP worker khác) + 1 cookies file riêng:
- `--parallel N` là **folder-level** (chunks `folder_list[i::N]`), mỗi worker chạy `_run_worker_loop` riêng qua ThreadPoolExecutor.
- `--cookies-dir <dir>` → quét `youtube-cookies*.txt` (sinh N bộ bằng script Camoufox, mỗi bộ session riêng) → worker `i` dùng file `i % len`.
- `set_worker(proxy_subpool=pool[i::N], cookies_file=...)` thread-local (`_WORKER_LOCAL`) → `_worker_proxy()` / `_worker_cookies()` ưu tiên hơn toàn cục.
- **Scale 20–32 Workers**: Máy Kibe (Dual Xeon E5-2680 v4 = 28c/56t, 64GB RAM) chạy ổn định ở cả 20 lẫn 32 worker (`--parallel 32`, CPU ~15–25% bình thường / ~55% khi burst download/whisper, RAM ~350MB–1GB, ~59–60 active threads). Proxy pool phân bổ đều cho từng worker subpool (`pool[i::N]`).
- **Quy trình đổi worker count / scale trên live run**:
  1. Kill các process cũ: `Get-CimInstance Win32_Process -Filter "CommandLine like '%download_by_niche%'"` -> `Stop-Process -Id <PID> -Force`.
  2. Relaunch với `--parallel <N>` (20 hoặc 32) giữ nguyên `--state-db`, `--runtime`, `--sources`, `--global-ledger-dir`, `--ledger-machine-id Kibe`, `--continue-on-insufficient`.
  3. `state.db` (WAL mode) + global ledger tự động resume các folder dở dang mà không mất dữ liệu hay tải lại video đã có.
  4. Verify: kiểm tra `(Get-Process -Id <PID>).Threads.Count` (~N+25 threads), log `report-*.jsonl` ghi nhận event download mới, và file `.mp4`/`.part.mp4` xuất hiện trong `D:\video goc`.
- ⚠️ **SQLite `database is locked` khi scale nhiều worker**: 20 worker cùng ghi `state.db` đồng thời với `BEGIN IMMEDIATE` sẽ gây lock nếu không cấu hình đúng:
  - Cần: `PRAGMA busy_timeout = 60000`, `PRAGMA journal_mode = WAL`, `PRAGMA synchronous = NORMAL`.
  - Trong Python: khai báo **một** `_DB_LOCK` ở cấp module và bọc toàn bộ transaction cạnh tranh (đặc biệt `reserve_folder`, các câu lệnh `connect_state()` đọc/ghi số lượng video khi download, cập nhật `output_path` sau renumber, và cập nhật `folders.status` ở cuối `run_folder`) bằng `with _DB_LOCK:`; không gọi `connect_state()` / `conn.execute` cập nhật DB trần ngoài lock giữa các worker threads.
  - `busy_timeout` chỉ giảm lỗi tranh chấp giữa process; nó không thay thế lock giữa các thread của cùng process. Với transaction `BEGIN IMMEDIATE`, serialize trước rồi retry backoff ngắn khi vẫn gặp `locked`.
  - Regression tối thiểu: chạy 20 worker reserve đồng thời trên DB tạm, xác nhận 40 folder được reserve và `errors=[]`; sau đó `py_compile` + `git diff --check`.
  - **Runtime isolation:** `state.db`/output/report của downloader là component riêng; không gán lỗi SQLite cho farm TikTok/ADB nếu chưa có bằng chứng process hoặc file dùng chung. Chỉ nhắc component liên quan trực tiếp trong báo cáo.
- ⚠️ **Hợp Nhất Master 69 Proxy Pool (MobiProxy + MikroTik LAN + Dedicated - User Invariant)**:
  - **Đủ 69 Proxies**: Gồm (1) 35 cổng MikroTik PPPoE (`mirotik1.taadaa.click:10001..10035` - user/pass: `admin@1:admin@1`), (2) 32 cổng MobiProxy (`test.taadaa.click` dải 5101..5108, 5111..5118, 5121..5128, 5131..5138), (3) 2 cổng Dedicated KhoaLee (`khoalee.duckdns.org:16002:5ns08q:AmLmaMJ0` & `khoalee.duckdns.org:16001:Gyx4k1:RzI0fc3o`).
  - **Lưu ý 2 Cổng KhoaLee**:
    - Port `16002`: `http://5ns08q:AmLmaMJ0@khoalee.duckdns.org:16002` (Sống 100%, 0.48s, IP: `116.111.194.124`).
    - Port `16001`: `http://Gyx4k1:RzI0fc3o@khoalee.duckdns.org:16001` (Trích xuất từ 9router DB; TCP open, dongle upstream có thể tạm timeout).
  - Cụm MikroTik PPPoE nằm tại IP LAN `192.168.110.2`. BẮT BUỘC truy cập trực tiếp `http://admin%401:admin%401@192.168.110.2:<port>` để đạt tốc độ nội bộ siêu tốc (~0.01 - 0.5s) và bypass rate-limit.
  - File pool chuẩn: `D:/Taadaa/Tiktok-video/proxy_pool_69.txt` (đồng bộ `proxy_pool_67.txt` và `D:/OneDrive/TaadaaData/proxy_combined_pool.txt`). Script generator: `python D:/Taadaa/Tiktok-video/scripts/generate_67_proxy_pool.py`.

### Giải pháp triệt tiêu Rate-Limit & Bot-Check YouTube Shorts (2026.08.19+):
1. **Deno JS Runtime**: Cài `pip install deno` để yt-dlp giải JavaScript challenge mà không văng cảnh báo `No supported JavaScript runtime`.
2. **Android Player Client API**: Tránh client mặc định `visionos` (hay bị YouTube báo `Video unavailable`). Thêm vào `ydl_opts`:
   `"extractor_args": {"youtube": {"player_client": ["android"]}}`
   Kéo video Shorts mượt mà ở tốc độ 15–30 MB/s.
3. **Xoay Proxy MikroTik LAN trực tiếp trong Downloader**: Mỗi request bắt socket qua cổng ngẫu nhiên `10001..10035` trên `192.168.110.2`, triệt tiêu hoàn toàn rủi ro dính rate-limit 1h của YouTube.
4. **Cách ly & Chống đụng hàng giữa Farm Admin và Farm Kibe**:
   - Máy Kibe xuất toàn bộ video ID đã tải (`state.db` + đĩa) sang `D:/OneDrive/SharedData/tiktok-video/kibe_downloaded_ids.json`.
   - Downloader trên Admin bắt buộc load file này và bỏ qua (`[CROSS-EXCLUDE]`) bất kỳ video ID nào Kibe đã sở hữu.
5. **Bộ Nguồn Xoay Tua Đa Ngách Triệu View (`source_manifest_viral_rotation.jsonl`)**:
   - Xoay tua đều giữa 6 niche có retention & loop rate cao nhất: (1) Thú cưng (Cute Pets), (2) Gái xinh / Dance visual, (3) Ẩm thực đường phố ASMR, (4) Oddly Satisfying / Phục chế thủ công, (5) Mẹo vặt đời sống / Ảo thuật, (6) Hài hước / Family / Cute Baby.
- ⚠️ **Cơ Chế Fail-Over Proxy Tức Thì (User: "Lỗi 1m proxy đó thì đổi proxy khác mà download")**:
  - Khi một cổng proxy trong pool bị lỗi (`Unable to connect to proxy`, `WinError 10061`, timeout, bot-check), `download_candidate()` và `discover_source()` bọc vòng lặp `max_dl_attempts = 3`, mỗi lần thử bốc ngay `next_proxy(args)` khác trong pool thay vì retry trên chính cổng chết.
- ⚠️ **Nghẽn Cổ Chai I/O Đĩa Cứng Trên `state.db` (Drive D: HDD vs Drive C: SSD)**:
  - Khi chạy đồng thời batch render FFmpeg và 20 worker download trên cùng ổ đĩa cơ 4TB `D:`, bảng `videos` trong `state.db` (hơn 46.000 dòng) nếu thiếu index sẽ khiến các câu query `SELECT COUNT(*)` mất tới 156 giây (2.5 phút!), làm kẹt `BEGIN IMMEDIATE` và đứng hình downloader hàng giờ (đứng yên 23/40 folder).
  - BẮT BUỘC tạo index: `idx_videos_folder_status`, `idx_videos_status`, `idx_videos_channel_status`, `idx_folders_status`. Khi cần, copy `state.db` sang ổ SSD `C:` (query giảm từ 156s xuống 0.013s). Chi tiết xem: `references/sqlite-io-bottleneck-and-proxy-failover-downloader.md`.
- **Script tiện ích chạy nhanh**: `run_download.bat <MachineId>` (e.g. `run_download.bat Admin` hoặc `run_download.bat Kibe`) đóng gói sẵn toàn bộ flags chuẩn để không cần nhớ lệnh. Khuyến nghị chạy bằng Python launcher `run_download_kibe.py` (cấu hình SSD `C:\CodexRuntime\tiktok-video\state.db`, `proxy_pool_67_direct.txt`, `--all-languages` bypass treo Whisper torch import), tránh dùng file `.bat` nếu có escape character `\t` (`\tiktok-video`) hoặc `\v` (`\venv-core024`).

### Quy trình lấp đầy 100% kho video khi nghẽn Insufficient Pool & Chống Trộn Kênh (2026-09-17..19)
- **Kỷ luật Bất biến: Tự động Auto-Discovery Inline, CẤM Dừng Hỏi (User Invariant 2026-09-18/19)**:
  1. **Không dừng hỏi khi hết nguồn**: Khi pool nguồn duyệt hết mà vẫn còn folder thiếu video, downloader BẮT BUỘC tự động kích hoạt inline `auto_discover_niche_source` để tìm kiếm kênh YouTube Shorts tiếng Việt mới theo niche, probe đạt $\ge 30$ video và tải ngay. CẤM tự ý dừng batch rồi quay ra hỏi user!
  2. **Cào Sâu (Deep Search) & Niche Fallback khi cạn ngách hẹp (User: "Cào sâu cho t, k thì đổi ngách khác")**:
     - *Cào sâu (Deep Search)*: Nâng query lên `ytsearch40` và `ytsearch30` kết hợp 4 biến thể từ khóa (`{label} shorts việt nam`, `{label} shorts`, `kênh {label} shorts việt`, `review {label} shorts việt nam`).
     - *Tự động đổi ngách (Niche Fallback)*: Khi cào sâu ngách gốc vẫn không ra kênh đạt $\ge 30$ Shorts, script BẮT BUỘC tự động duyệt sang các ngách dồi dào nguồn nhất farm (`cuoi`, `khampha`, `amthuc`, `meovat`, `review`, `phim`, `tintuc`, `congnghe`). Khi tìm được kênh mới, cập nhật lại `niche` của folder trong `state.db` và tải ngay mà KHÔNG ĐƯỢC return False kết thúc sớm!
  3. **Multi-Source Retry & Lặp đến khi đủ video (User: "k đủ 30 video/folder thì phải download lại, tìm kênh mới đến khi nào down đủ thì thôi")**:
     - Khi một kênh không đủ `min_videos` (dù tải được một phần), downloader xóa sạch media dở dang của kênh đó (`clean_incomplete_folder_and_db`), reset record trong DB để bảo đảm 1 folder = 1 kênh duy nhất.
     - Tiếp tục xoay vòng sang source tiếp theo trong pool (`max_source_attempts`). Nếu pool có sẵn cạn kênh, lập tức gọi inline `auto_discover_niche_source` để cào Shorts tiếng Việt mới trên YouTube và kéo tiếp.
     - Chỉ dừng khi folder đã đạt $\ge min\_videos$ (hoặc chạm ngưỡng giới hạn an toàn attempt).
  4. **Kỷ luật Nghiệm thu Chốt phiên Bắt buộc qua AI Reviewer (Sol Scorecard 100đ)**:
     - Khi chốt phiên sửa code Downloader/Render, CẤM bỏ qua bước gọi AI Reviewer.
     - BẮT BUỘC chạy `python D:/Taadaa/tools/closeout_gate.py` (hoặc gửi packet kèm test execution log + runtime watchdog evidence sang OmniRoute `:20129` model `review` / `sol-high`).
     - Chỉ chốt phiên khi đạt điểm $\ge 85/100$ và `VERDICT: APPROVED`.
  5. **Khôi phục Render & Download sau khi máy Host Reboot / Reset**:
     - Máy farm sau khi khởi động lại, các tiến trình ngầm (background jobs) sẽ bị mất.
     - Phục hồi Render Slot 7 & 8: Chạy `powershell -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_kibe_slot7_slot8_render.ps1 -StartMachine 1 -EndMachine 80 -Parallel 1` ở chế độ ngầm (`Start-Process ... -WindowStyle Hidden`).
     - Phục hồi Downloader: Khởi động `python D:\Taadaa\Tiktok-video\run_download_kibe.py` (20 workers, SSD NVMe `state.db`, proxy pool 57 ports trực tiếp, cookies Netscape).
     - Đối soát kiểm tra: Chạy watchdog `farm_render_download_watchdog.py` để verify cả 2 luồng đều chuyển sang 🟢 **Đang chạy** và clip render/download tăng đều thực tế.
  6. **Bảo đảm An toàn Tuyệt đối 1 Folder = 1 Kênh (Clean-on-Insufficient)**: Khi folder tải xong nhưng số lượng video không đạt chuẩn tối thiểu ($\text{count} < args.min\_videos$):
     - BẮT BUỘC gọi `clean_incomplete_folder_and_db(folder_num, output_dir, args)` xóa sạch 100% file media dở dang (`*.mp4`, `*.part*`, `*.jpg`, `*.json`) trong thư mục folder trên đĩa (`D:\video goc\<folder_num>`).
     - Xóa sạch toàn bộ bản ghi của folder đó trong bảng `videos` của `state.db`: `DELETE FROM videos WHERE folder = ?`.
     - Reset trạng thái folder: `folders.status = 'insufficient_pool'`, `folders.source_channel = NULL`, `folders.video_count = 0`.
     - Tuyệt đối không để lại file dở dang của kênh cũ trên đĩa, tránh rủi ro khi gán kênh mới vào sẽ biến thành 1 folder chứa video của 2 kênh khác nhau.

Khi batch download chạy hết dải 640 folder và dừng lại nhưng kho chưa đủ 100% $\ge 30$ video (còn lại các folder `insufficient_pool` do cạn nguồn ngách hoặc đứt gãy mạng):
1. **Kiểm tra phân bổ thiếu & đối soát video dở (BẮT BUỘC để chống trộn kênh)**:
   - Đọc trực tiếp từ SSD NVMe `state.db` (`C:\CodexRuntime\tiktok-video\state.db`):
     ```sql
     SELECT folder_num, niche, video_count, status FROM folders WHERE status = 'insufficient_pool';
     -- Kiểm tra video đã tải thật trong DB cho các folder này:
     SELECT folder, status, count(*) FROM videos WHERE folder IN (...) GROUP BY folder, status;
     ```
   - ⚠️ **Nguyên tắc bất biến: 1 folder = 1 kênh duy nhất (User: "K lẽ thành 1 folder chứa nguồn 2 kênh cùng niche à")**:
     - **Báo cáo User**: Luôn giải thích rõ ràng tách bạch giữa 2 nhóm, khẳng định trước: "Folder dở dang giữ 100% kênh cũ, chỉ folder trống 0 video mới gán kênh mới" để tránh user hiểu lầm là gộp 2 kênh vào 1 folder.
     - **Nhóm dở dang ($\ge 1$ video trên đĩa / DB)**: Do proxy rớt hoặc bot-check giữa chừng (`download_no_media`) chứ kênh gốc không hề thiếu video. **CẤM reset `source_channel = NULL`** hay cấp kênh mới (sẽ gây trộn 2 kênh vào 1 folder). Phục hồi candidate failed về `discovered`:
       ```sql
       UPDATE videos SET status = 'discovered', rejection_reason = NULL 
       WHERE folder IN (<danh_sach_folder_do_dang>) AND status = 'failed' AND rejection_reason = 'download_no_media';
       UPDATE folders SET status = 'pending' WHERE folder_num IN (<danh_sach_folder_do_dang>);
       ```
     - **Nhóm trống hoàn toàn (0 video)**: Reset về pending và giải phóng `source_channel = NULL` để đón nguồn mới:
       ```sql
       UPDATE folders SET status = 'pending', source_channel = NULL, video_count = 0 
       WHERE status = 'insufficient_pool' AND folder_num NOT IN (<danh_sach_folder_do_dang>);
       ```
     - **Trường hợp kênh cũ thực sự cạn video (<30 video)**: Bắt buộc di chuyển toàn bộ video cũ sang thư mục cách ly `D:\video goc\_trash_incomplete_named\<folder_num>` và xóa record trong DB trước khi gán kênh mới để bảo đảm folder 100% video cùng 1 kênh.
2. **Cơ chế Auto-Discovery tích hợp trong Downloader (`download_by_niche.py`)**:
   - Khi folder duyệt hết pool nguồn sẵn có mà không còn kênh đủ $\ge 30$ video, downloader tự động kích hoạt `auto_discover_niche_source(niche, args, ...)` ngay trước khi ghi nhận `insufficient_pool`.
   - Tìm kiếm YouTube Shorts theo nhãn niche (`ytsearch15:<niche.label> shorts việt nam`), probe tab `/shorts`, kiểm tra exclusion & language gate.
   - Khi tìm được kênh đạt chuẩn $\ge 30$ Shorts: tự động claim ledger, append vào `sources.qualified30.json`, insert candidates vào `state.db` và kéo video ngay mà không dừng batch.
   - ⚠️ **Kỷ luật giao tiếp chốt phiên & giải trình chống trộn kênh (2026-09-17)**:
     - Khi user hỏi *"sao lại tìm theo niche, không lẽ 1 folder chứa 2 kênh?"*: Phải trả lời khẳng định ngay lập tức là **KHÔNG BAO GIỜ TRỘN KÊNH**, giải thích rành mạch: folder dở dang chỉ kéo nốt kênh cũ; folder trống 0 video mới kéo kênh mới theo niche.
     - Khi user giục *"chốt phiên"* hoặc hỏi *"xong chưa"* trong lúc AI Reviewer reject: Không dây dưa giải thích chi tiết kỹ thuật quá sâu làm chậm phiên; thông báo rõ lý do ngắn gọn (Sol review bảo mật/atomic write), hoàn thiện nhanh các điểm chặn và đưa phiên về trạng thái an toàn.
3. **Cào thủ công bổ sung nguồn mục tiêu (nếu chạy độc lập)**:
   - Dùng `scripts/fast_targeted_qualify_stream.py` hoặc `feed_qualified_sources_and_resume.py`.
4. **Khởi động lại downloader ngầm**:
   - Chạy `python run_download_kibe.py` (cấu hình `--parallel 20`, `--start-folder 481`, `--total-folders 640`, `--continue-on-insufficient`, `--all-languages`, `--proxy-pool proxy_pool_67_direct.txt`).
   - Kiểm tra PID và đuôi log `download_run.log` để xác nhận video bắt đầu kéo về.

### Phân tách và dọn rác khi bị lẫn 2 kênh / trùng số folder (Mixed Named & Numbered Files)
- **BẮT BUỘC ĐÁNH SỐ THỨ TỰ `1.mp4..N.mp4` (Cả Video Gốc và Video Render `D:\TIKTOK-videonuoinick`)**:
  - `path_resolver.py` của upload workflow đọc cột `Video Đã Đăng` từ workbook và resolve đường dẫn cứng `{media_source_root}/{Folder Video}/{video_number}.mp4`.
  - Nếu file mang tên dài/tiêu đề (vd: `tik_tik3-stt347...mp4` hay `Tiêu đề [id].mp4`), upload sẽ lập tức văng `PathResolverError: Video file not found: ...\1.mp4` $\rightarrow$ **toàn bộ máy farm bị dừng đăng video**.
  - **Video gốc**: Downloader tạm lưu `[title] [id].mp4` khi đang kéo để tránh đụng độ luồng, nhưng ngay khi đủ $\ge 30$ video PHẢI gọi `renumber_mp4_files()` để chuẩn hóa thành `1.mp4..N.mp4` và cập nhật `output_path` trong `state.db`.
  - **Fail-safe renumber**: Hàm `renumber_mp4_files` trong `run_folder` phải được bọc `try/except` ghi log warning thay vì để exception `FileExistsError` làm sập toàn bộ batch 20 workers khi gặp folder đã tồn tại file số cũ.
  - **Video render (`D:\TIKTOK-videonuoinick`)**: 100% file render phải là `1.mp4..N.mp4`. Nếu gặp folder cũ mang tên prefix/tiêu đề, phải sort và renumber về `1.mp4..N.mp4` trước khi đẩy sang máy farm.
- **Hiện tượng**: Folder xuất hiện cả file số chuẩn (`1.mp4..N.mp4`) và file tên tiêu đề (`<title> [youtube_<id>].mp4`), nguyên nhân do chạy nhiều state.db hoặc batch mới ghi đè vào folder cũ chưa hoàn tất renumber.
- **Quy trình chuẩn hóa kho**:
  1. **Nhóm $\ge 30$ video tên tiêu đề (đủ chuẩn batch)**: Tìm các slot folder trống/chưa có video trong dải 1..480 (hoặc mở rộng), di chuyển toàn bộ file sang folder mới, đổi tên tuần tự thành `1.mp4..N.mp4`, copy/sinh avatar và đánh dấu `status = 'complete'`, `video_count = N` trong `state.db`.
  2. **Nhóm $< 30$ video tên tiêu đề (dở dang/rác)**: Di chuyển sang thư mục cách ly `D:\video goc\_trash_incomplete_named\<folder_num>` để trả lại folder gốc sạch 100% một kênh duy nhất.
  3. **Đồng bộ lại `folders` trong `state.db`**: Quét toàn bộ `D:\video goc\1..480`, đếm số file `.mp4`: nếu $\ge 30$ cập nhật `complete`, nếu $0$ hoặc $< 30$ cập nhật `pending` (video_count = 0) để sẵn sàng cho downloader kéo nguồn mới sạch.
  4. **Khởi động downloader ngay**: Sau khi fix và dọn kho, khởi chạy lại batch download ngay bằng đúng 1 process, xác nhận log `report-*.jsonl` và trạng thái `state.db` trước khi báo cáo.

### ⚠️ Ledger liên máy (BẮT BUỘC khi chạy download có admin dùng chung)
KHÔNG truyền `--global-ledger-dir` → video tải xong KHÔNG ghi ledger → máy admin **tải trùng**!
- Chạy với: `--global-ledger-dir "D:/OneDrive/SharedData/tiktok-video/global-ledger" --ledger-machine-id Kibe`
- Mỗi máy ghi `Admin.jsonl`/`Kibe.jsonl`, cả 2 đọc TẤT CẢ `*.jsonl` = dedup 2 chiều (source/video/hashes)
- Quên rồi → backfill từ state.db (chi tiết: `references/worker-isolation-ledger.md`)

### Quy trình thay thế nguồn & Reset folder khi nguồn cũ cạn video (Clean-Replace Source)
Khi một folder bị thiếu video do nguồn cũ cạn Shorts hoặc bị nghẽn `insufficient_pool`, quy trình chuẩn để thay nguồn sạch 100%:
1. **Dọn sạch đĩa**: Xóa sạch toàn bộ video và file tạm trong thư mục `D:\video goc\<folder_num>`.
2. **Reset State.db**:
   - `DELETE FROM videos WHERE folder = <folder_num>;`
   - `UPDATE folders SET status = 'pending', source_channel = NULL, video_count = 0, completed_at = NULL WHERE folder_num = <folder_num>;`
3. **Dọn sạch Ledger claim**: Xóa dòng claim của `<folder_num>` và channel cũ trong toàn bộ file `D:\OneDrive\SharedData\tiktok-video\global-ledger\*.jsonl` để giải phóng namespace (tránh `read_source_claims` tự khôi phục lại kênh lỗi).
4. **Chọn nguồn mới**:
   - Tra cứu trong `sources.qualified30.json` theo niche tương ứng.
   - Kiểm tra đối chiếu với `global-ledger` để đảm bảo kênh chưa bị máy khác claim.
   - Probe nhanh tab `/shorts` qua yt-dlp để xác nhận kênh có $\ge 40$ Shorts còn hoạt động.
5. **Xoay Proxy & Format Fallback chống 403**:
   - Khi tải YouTube Shorts, nếu gặp HTTP 403 do cookies phiên cũ, xoay proxy di động từ `PROXYgandienthoai.xlsx` (`test.taadaa.click:51xx`).
   - ⚠️ **Bắt buộc URL-encode mật khẩu proxy**: Pass chứa `#` (`%23`), `!` (`%21`) để tránh `yt-dlp` lỗi `Failed to parse proxy URL`.
   - Sử dụng format `18/b[ext=mp4]/best` hoặc `bv*[vcodec^=avc]+ba[ext=m4a]` kèm `-map_metadata -1` để stream MP4 chuẩn tải nhanh và không dính rate-limit.
6. **Chuẩn hóa & Ghi nhận**:
   - Tải tối thiểu $\ge 30$ video (khuyến nghị 35–42 video).
   - Đánh số thứ tự tuần tự `1.mp4..N.mp4`.
   - Sinh `avatar.jpg` chuẩn từ frame video đầu tiên (crop vuông 512x512).
   - Cập nhật bản ghi `videos` và `folders.status = 'complete'`, `folders.source_channel = <channel_url>`, `folders.video_count = N` trong `state.db`.

### ⚠️ Bẫy video DÀI: fallback `/shorts` → `/videos` (user bắt buộc — "đừng bảo đi tải video bth của youtube")
`discover_source` (download_by_niche ~297) build listing_urls = **`/shorts` TRƯỚC, fallback `/videos`**. Kênh KHÔNG có Shorts tab → log "This channel does not have a shorts tab" → fallback tab `/videos` = video thường YouTube → tải nhầm phim/series/vlog 1-3h! (Đã từng tải 439 file = 250GB rác: phim hài 3.6GB, series 10.982s, clip du lịch 500-700s).
- **Fix đã encode**: `match_filter "duration < 300"` trong `yt_options(download=True)` → yt-dlp tự loại video >300s trước khi tải (kể cả từ fallback /videos)
- ⚠️ **Cú pháp match_filter**: yt-dlp KHÔNG hỗ trợ `is not None` — `"duration is not None and duration < 300"` raise ValueError. Dùng `"duration < 300"` (duration unknown cũng bị loại = an toàn, chấp nhận)
- Mốc 300s vs 180s: **chốt 300s** (TikTok cho đăng tối đa 10 phút / 600s nên 300s an toàn, vừa không bỏ sót video 3-5p, vừa chặn phim/series dài)
- **Lưu xong rồi dọn rác**: script `scripts/remove-long-videos.py` (probe ffprobe duration → xóa >300s → xóa record state.db + perceptual_hashes + reset folder complete bị ảnh hưởng → insufficient_pool để re-download bù). Đã chạy: xóa 439 file / 250.1GB, reset 15 folder.

### Quy trình thay thế nguồn & Reset folder khi nguồn cũ cạn video (Clean-Replace Source)
Khi một folder bị thiếu video do nguồn cũ cạn Shorts hoặc bị nghẽn `insufficient_pool`, quy trình chuẩn để thay nguồn sạch 100%:
1. **Dọn sạch đĩa**: Xóa sạch toàn bộ video và file tạm trong thư mục `D:\video goc\<folder_num>`.
2. **Reset State.db**:
   - `DELETE FROM videos WHERE folder = <folder_num>;`
   - `UPDATE folders SET status = 'pending', source_channel = NULL, video_count = 0, completed_at = NULL WHERE folder_num = <folder_num>;`
3. **Dọn sạch Ledger claim**: Xóa dòng claim của `<folder_num>` và channel cũ trong toàn bộ file `D:\OneDrive\SharedData\tiktok-video\global-ledger\*.jsonl` để giải phóng namespace.
4. **Chọn nguồn mới**:
   - Tra cứu trong `sources.qualified30.json` theo niche tương ứng.
   - Kiểm tra đối chiếu với `global-ledger` để đảm bảo kênh chưa bị máy khác claim.
   - Probe nhanh tab `/shorts` qua yt-dlp để xác nhận kênh có $\ge 40$ Shorts còn hoạt động.
5. **Xoay Proxy & Format Fallback chống 403**:
   - Khi tải YouTube Shorts, nếu gặp HTTP 403 do cookies phiên cũ, xoay proxy di động từ `PROXYgandienthoai.xlsx` (`test.taadaa.click:51xx`).
   - ⚠️ **Bắt buộc URL-encode mật khẩu proxy**: Pass chứa `#` (`%23`), `!` (`%21`) để tránh `yt-dlp` lỗi `Failed to parse proxy URL`.
   - Sử dụng format `18/b[ext=mp4]/best` hoặc `bv*[vcodec^=avc]+ba[ext=m4a]` kèm `-map_metadata -1` để stream MP4 chuẩn tải nhanh và không dính rate-limit.
6. **Chuẩn hóa & Ghi nhận**:
   - Tải tối thiểu $\ge 30$ video (khuyến nghị 35–42 video).
   - Đánh số thứ tự tuần tự `1.mp4..N.mp4`.
   - Sinh `avatar.jpg` chuẩn từ frame video đầu tiên (crop vuông 512x512).
   - Cập nhật bản ghi `videos` và `folders.status = 'complete'`, `folders.source_channel = <channel_url>`, `folders.video_count = N` trong `state.db`.

### Avatar tự động tích hợp trong download
- `make_avatar_for_folder` chạy ngay khi mỗi folder download xong đủ video (không cần đợi render).
- Thứ tự ưu tiên (chuẩn mới): 1. Người (face detect) -> 2. Động vật (YOLO theo niche) -> 3. Frame sáng 512x512. Kênh thật chỉ dùng khi cả 3 fail.

### Batch Recovery & Đồng bộ State.db khi chạy bù (Resume incomplete folders)
- **Nguồn chuẩn**: BẮT BUỘC dùng `--sources "D:/OneDrive/SharedData/tiktok-video/sources.qualified30.json"` (294+ sources đã qualify). Tránh dùng nhầm file supplement/pilot tạm thời chỉ có vài chục kênh.
- **Refresh đồng loạt 20 Cookies files**: Khi cookies hết hạn (>48-96h), dùng Camoufox xuất 1 chuỗi Netscape cookies rồi ghi đè đồng loạt ra `youtube-cookies-01.txt` đến `youtube-cookies-20.txt` + `youtube-cookies.txt`.
- **Sync disk vs state.db trước khi resume**:
  - Quét thực tế `D:\video goc\<1..480>`: folder nào `< 30` video thì cập nhật `folders` trong `state.db` về `status = 'pending'`, `source_channel = NULL`, `video_count = <count_thực_tế>`.
  - Cập nhật đúng slug niche cho từng folder theo formula `(folder_num - 1) % len(niches_pool)`.
  - Giúp `eligible_sources` giải phóng các source_channel bị kẹt từ run cũ để cấp phát kênh hợp lệ mới cho các folder thiếu.

### Xử lý nghẽn Insufficient Pool và Quy trình Stream Discovery bổ sung nguồn (2026-09-16)
- **Hiện tượng**: Downloader quét hết dải folders (ví dụ 481..640) và dừng lại tự nhiên, để lại các folder ngách (anime, anh, dochai, thien, mevabe, vantay...) ở trạng thái `insufficient_pool` (video_count = 0 hoặc < 30) do cạn nguồn kênh Shorts trong `sources.qualified30.json`.
- **Phân biệt tiến trình dừng vs Lỗi/Treo**:
  - Không nhầm lẫn giữa downloader bị crash với downloader hoàn tất lượt quét. Kiểm tra `psutil` xem tiến trình có còn sống hay không.
  - Kiểm tra số folder `insufficient_pool` và số folder `complete` trong `C:\CodexRuntime\tiktok-video\state.db` (NVMe SSD).
- **Quy trình cào vét và phục hồi nguồn mới (`fast_targeted_qualify_stream.py`)**:
  1. Lấy danh sách các niche ngách bị thiếu từ các folder `status IN ('pending', 'insufficient_pool') AND (video_count < 30 OR video_count IS NULL)` trong `C:\CodexRuntime\tiktok-video\state.db`.
  2. Dùng yt-dlp với cookies Netscape probe các query search Shorts (`ytsearch10:<niche> shorts việt nam`) lọc các kênh chưa bị claim trong `D:\OneDrive\SharedData\tiktok-video\global-ledger`.
  3. Thẩm định số lượng Shorts (`playlist_items: "1-65"`), chọn các kênh có $\ge 30$ Shorts và stream nối tiếp vào `D:\OneDrive\SharedData\tiktok-video\sources.qualified30.json`.
  4. Reset trạng thái DB: `UPDATE folders SET status = 'pending', source_channel = NULL WHERE status = 'insufficient_pool';`.
  5. Kích hoạt lại `download_by_niche.py` với launcher `run_download_kibe.py` (sử dụng `proxy_pool_67_direct.txt` và cờ `--all-languages` để bypass nghẽn CPU Whisper).
  6. Sau khi khởi chạy, xác minh PID tiến trình và kiểm tra `videos` table trong `state.db` để thấy các video candidate mới liên tục chuyển sang `discovered` và tiến hành tải về đĩa.

### Ngưỡng min-videos & Xử lý nghẽn Insufficient Pool (BẮT BUỘC giữ chuẩn $\ge 30$)
- **Quy tắc nuôi nick farm**: 1 máy 3 nick (mỗi ca 1 nick, 2 ngày nick mới chạy lại phiên 3 và upload 1 video). 1 folder cần tối thiểu $\ge 30$ video để nick đủ video đăng liên tục trong ít nhất 2 tháng (60 ngày) mà không bị lỗi `PathResolverError: Video file not found` khi cột `Video Đã Đăng` tăng dần.
- **CẤM tự ý hạ `--min-videos < 30`** khi gặp `insufficient_pool`: Việc hạ xuống 20–25 video sẽ sớm làm cạn kho video khi nick đăng qua ngày thứ 20, gây dừng luồng đăng của máy farm.
- **Xử lý chuẩn khi nghẽn Insufficient Pool (Auto-Discovery & Qualify Nguồn Mới)**:
  1. Giữ nguyên `--min-videos 30`.
  2. Xác định các niche ngách đang thiếu nguồn từ các folders `status = 'pending'` trong `state.db`.
  3. Quét YouTube search (`ytsearch10:<niche_label> shorts việt nam`) để tìm các kênh Shorts tiếng Việt tiềm năng.
  4. Lọc đối chiếu với `global-ledger` (`read_source_keys`) để loại trừ 100% các kênh đã claim giữa các máy (Admin/Kibe).
  5. Dùng cookies Camoufox probe song song số lượng Shorts (`playlist_items: "1-65"`), chọn các kênh có $\ge 30$ Shorts.
  6. Ghi nối tiếp vào `sources.qualified30.json`, reset các folder thiếu về `status = 'pending'`, `source_channel = NULL` và khởi động lại downloader batch.
- ⚠️ **Đồng bộ định dạng Cookies Netscape**:
  - Khi dùng đa luồng với `--cookies-dir`, tất cả các file `youtube-cookies-01.txt..20.txt` phải ở chuẩn định dạng Netscape hợp lệ. Nếu 1 file bị lỗi định dạng (text rỗng hoặc định dạng sai), yt-dlp sẽ báo `does not look like a Netscape format cookies file` và văng HTTP 403 / `[Errno 22]`. Khắc phục: copy đồng loạt nội dung từ `youtube-cookies.txt` chuẩn sang toàn bộ dải `youtube-cookies-*.txt`.



### Nguồn TikTok song song với YouTube (yt-dlp headers + Direct TikWM Fallback + Search Discovery)
- Đã mở lại platform TikTok song song với YouTube (50/50 target pool trong `download_by_niche.py` & `source_pool_builder.py`).
- **Profile Scraping O(1) qua yt-dlp**: Dùng `yt-dlp --flat-playlist --dump-json "https://www.tiktok.com/@<handle>"` trích xuất trọn vẹn 100% video list và metadata chi tiết (views, likes, comments, saves, duration, upload date, secUid) mà không bị kẹt bởi WAF hay web slider captcha.
- ⚠️ **Bẫy cào profile TikTok bằng yt-dlp (`Unexpected response from webpage request` / `Unable to extract secondary user ID`)**:
  - Profile extractor của `yt-dlp` bị chặn anti-bot hoàn toàn trên các trang cá nhân TikTok.
  - **Khắc phục Discovery 2 tầng**:
    1. **Camoufox Web Profile**: Render trang cá nhân và bắt response `/api/post/item_list/` để trích xuất `itemList` video IDs.
    2. **Public Search Fallback (chống CAPTCHA)**: Khi TikTok bật puzzle slider ("Drag the slider to fit the puzzle"), tự động fallback sang tìm kiếm công khai qua DDGS/Bing với query `site:tiktok.com/@<handle>/video/` để lấy dải URL video hợp lệ.
    3. ⚠️ *DDGS syntax*: Không dùng `with DDGS(...)` (lỗi context manager); khởi tạo trực tiếp `search = DDGS(timeout=30)` rồi gọi `search.text(...)`.
- ⚠️ **Bẫy tải stream video TikTok đơn lẻ**:
  - `yt-dlp` thường xuyên bị chặn khi tải stream MP4 trực tiếp của TikTok.
  - **Khắc phục**: Luôn ưu tiên gọi **Direct Fallback trước (`download_tiktok_direct` qua TikWM `https://tikwm.com/api/?url=...`)**, chỉ fallback về `yt-dlp` nếu direct resolver thất bại.
- ⚠️ **Gộp Pool Nguồn Song Song (`sources.combined_yt_tt.json`)**:
  - File `sources.qualified30.json` gốc chỉ có YouTube (294 sources). Để chạy tải song song 50/50, quét bổ sung kênh TikTok phủ đủ 80 niches rồi gộp thành `sources.combined_yt_tt.json` (~870 sources), sau đó cập nhật `folders.platform` trong `state.db` phân bổ đều giữa `tiktok` và `youtube`.

### Quy trình TikTok hiện hành: discovery tách khỏi download
- Không coi `yt-dlp` profile extractor là đường duy nhất. Khi profile trả `Unexpected response` hoặc `Unable to extract secondary user ID`, giữ YouTube route nguyên trạng và chuyển discovery TikTok theo thứ tự: (1) Camoufox render profile, bắt response public `/api/post/item_list/` và lấy `itemList`/`item_list`; (2) nếu profile bị challenge `Drag the slider to fit the puzzle`, dùng DDGS/Bing public search với `site:tiktok.com/@<handle>/video/`; (3) chỉ dùng URL video public, không lưu cookie, token, `X-Bogus`, `X-Gnarly` hay browser state.
- Download TikTok: gọi `download_tiktok_direct()` qua TikWM trước; chỉ fallback về yt-dlp khi direct resolver thất bại. Discovery có thể bị anti-bot nhưng URL video cụ thể vẫn có thể tải MP4.
- DDGS bản đang dùng có thể không hỗ trợ context manager; dùng `search = DDGS(timeout=30)` rồi `search.text(...)`, không dùng `with DDGS(...)` nếu chưa kiểm tra API.
- Regex URL phải chấp nhận dạng `https://www.tiktok.com/@handle/video/<15-25 digits>` và loại query string trước khi dedupe.
- Canary gate bắt buộc: discovery một profile thật phải trả candidate URLs; tải ít nhất một URL bằng đúng hàm production; kiểm tra file tồn tại, byte size > 1 KiB và `ffprobe` đọc được duration/size. Không báo TikTok đã tải được chỉ vì wrapper exit 0 hoặc report record-level.
- Nếu Camoufox trả CAPTCHA trên nhiều profile, ghi rõ `BLOCKED_DISCOVERY_CAPTCHA`; không bypass CAPTCHA và không chạy batch rộng với source pool rỗng. Tách kết luận “direct URL download OK” khỏi “profile discovery/batch OK”. Chi tiết: `references/tiktok-discovery-and-direct-download.md`.

### Đối chiếu lịch sử: profile crawl runtime không đồng nghĩa URL cache thủ công
- Khi người dùng hỏi vì sao run cũ tải đơn giản, phải kiểm tra cả revision cũ, source manifest và `state.db`. Code cũ có thể gọi `yt_dlp.extract_info(source.url)` trên profile, tự sinh `/video/<id>` entries rồi persist chúng vào DB; URL cụ thể trong DB là bằng chứng runtime discovery, không tự động chứng minh có người chuẩn bị cache.
- So sánh tách ba lớp: (1) route discovery cũ/mới, (2) manifest hiện tại (`video_urls`), (3) rows/report thực tế (`source_url LIKE '%/video/%'`, status downloaded/failed). Không kết luận “manifest cũ có sẵn URL” chỉ vì DB lịch sử có URL video.
- Trả lời ngắn theo facts: trước đây profile extractor còn hoạt động; hiện profile bị anti-bot/CAPTCHA; direct resolver từng URL vẫn có thể hoạt động. Không hạ ngưỡng folder hoặc ghép kênh trước khi chứng minh discovery là bottleneck. Chi tiết: `references/tiktok-historical-discovery.md`.

### Bẫy cào nguồn tự động lọt kênh ngoại quốc / tiếng Anh (User: "Toàn kênh nc ngoài à")
- **Hiện tượng**: Khi cào bổ sung nguồn bằng search query YouTube (ví dụ query có từ mượn như `marketing shorts`, `anime shorts`, `review shorts`), YouTube trả về các kênh tiếng Anh/quốc tế đình đám (như `ThinkMediaTV`, `BethanyAtazadeh`). Nếu nạp thẳng vào `sources.qualified30.json` và bật `--all-languages`, toàn bộ máy farm sẽ tải video tiếng Anh/nước ngoài về kho nuôi nick.
- **Quy chuẩn lọc kênh tiếng Việt chuẩn 100% (Strict Vietnamese Gate)**:
  1. **Query bắt buộc ngữ cảnh Việt**: Phải có đuôi `shorts việt nam`, `tiếng việt shorts`, `kênh <label> shorts việt`.
  2. **Kiểm tra dấu tiếng Việt (Regex Diacritics Gate)**:
     - Regex bắt dấu: `[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]`.
     - Nếu tên kênh có dấu tiếng Việt: bắt buộc $\ge 30\%$ tiêu đề Shorts phải có dấu tiếng Việt.
     - Nếu tên kênh KHÔNG dấu: bắt buộc $\ge 55\%$ tiêu đề Shorts phải có dấu tiếng Việt chuẩn. Kênh nào dưới ngưỡng này bị loại thẳng tay (`REJECTED_FOREIGN`).
  3. **Streaming Save**: Khi cào hàng trăm kênh, bắt buộc ghi lưu file `sources.qualified30.json` cuốn chiếu (mỗi 25 kênh hoàn tất lưu một lần) để tránh bị timeout terminal làm mất kết quả probe.

### Quy tắc duyệt âm thanh cho kênh tiếng Việt & Bẫy Language Score Throttling
- ⚠️ **Bẫy `candidate_passes_language_source_gate` lọc bỏ video không dấu**:
  - Ban đầu logic yêu cầu tiêu đề/mô tả phải có dấu tiếng Việt (`metadata_score >= 0.15`) hoặc `verified_vn = True`.
  - Hậu quả: Video Shorts/TikTok gõ không dấu (e.g. `sofa gia re`, `review quan an`) hoặc video nhạc trend bị loại ngay lúc quét kênh $\rightarrow$ số candidate rớt xuống dưới `min_videos` $\rightarrow$ folder bị đánh dấu `insufficient_pool`.
  - **Khắc phục**: Với các kênh đã nằm trong pool nguồn chọn lọc (`sources.combined_yt_tt.json`), hàm `candidate_passes_language_source_gate()` phải trả `True` để chấp nhận toàn bộ video làm ứng viên.
- ⚠️ **Bẫy `verified_vn = False` & Review Queue Throttling (Video tải về nhiều nhưng không vào đĩa)**:
  - Toàn bộ kênh cào tự động từ Discovery có cờ `verified_vn = False`. Nếu yêu cầu chặt chẽ giọng nói tiếng Việt từ Whisper, **~70% video sẽ bị loại** (`audio_detection_failed` do nhạc nền, video không lời, meme, thú cưng...).
  - Khi `is_trusted_vn = True`, nếu video âm thanh không xác định/nhạc/không lời được gán `score = 0.55` + metadata `0.15` = `0.70`, nhưng ngưỡng nhận yêu cầu `score >= 0.75` $\rightarrow$ video bị ném vào `review_queue` với lý do `language_score_below_threshold` thay vì lưu vào đĩa đếm số.
  - **Quy tắc chuẩn**: Các kênh đã nằm trong nguồn qualified mặc định được tin tưởng (`is_trusted_vn = True`, gán `score = max(score, 0.75)` khi không có ngoại ngữ). Chỉ loại bỏ duy nhất khi Whisper phát hiện 100% là tiếng nước ngoài (`audio_lang_not_vi`).
  - **Chẩn đoán nhanh**: Đọc file report mới nhất `D:\CodexRuntime\tiktok-video\report-*.jsonl` để đếm tỷ lệ:
    `Counter(e.get('status') for e in events)` và `Counter(e.get('rejection_reason') for e in events)`
    Nếu thấy `review` chiếm đa số với lý do `language_score_below_threshold`, nguyên nhân là do kẹt ngưỡng điểm.
  - **Kiểm tra thông lượng thực tế**: Đo số file hoàn tất trong 5 phút gần nhất:
    `[f for f in glob.glob('D:/video goc/**/*.mp4', recursive=True) if os.path.getmtime(f) > (time.time() - 300) and not f.endswith('.part.mp4')]`.
- **Chẩn đoán nhanh Downloader bị chững / User hỏi "Sao lại đang dừng download"**:
  0. **Phân biệt Batch hoàn tất tự nhiên vs Lỗi/Crash**:
     - Khi watchdog định kỳ `farm-render-download-watchdog` (1h/lần) báo `Trạng thái download: ⚪ Đang dừng`, user thường hỏi vì sao dừng.
     - Kiểm tra nhanh O(1) qua database trên ổ SSD NVMe `C:\CodexRuntime\tiktok-video\state.db` (tuyệt đối KHÔNG quét `os.walk` đĩa cơ 4TB `D:\video goc` vì sẽ timeout >180s):
       `python -c "import sqlite3; conn = sqlite3.connect('C:/CodexRuntime/tiktok-video/state.db'); print(conn.execute('SELECT status, count(*) FROM folders GROUP BY status').fetchall())"`
     - Quy mô hiện tại của farm Kibe là **640 folders** (80 máy × 8 slot). Nếu tổng số dòng `folders` đã đạt 640 (vd: 585 `complete`, 27 `complete_partial`, 28 `insufficient_pool`) và process không còn trong tasklist, **tiến trình đã hoàn thành quét trọn vẹn 100% dải folder từ start đến 640**, không phải do crash hay đơ treo.
     - ⚠️ **Định nghĩa chuẩn của `complete_partial`**: Trong `download_by_niche.py`, `complete_partial` là folder có `video_count >= min_videos (30)` nhưng `< target_videos (45)`. Các folder này (vd: 31–44 video) **HOÀN TOÀN ĐẠT CHUẨN nuôi nick**, không phải lỗi hay dở dang! Tổng số folder đạt chuẩn thực tế là `complete` + `complete_partial` (612/640 = 95.6%). Khi đối soát kho, tránh nhầm tưởng chỉ có nhóm `complete` mới dùng được.
     - Các folder còn lại dừng do cạn nguồn Shorts tiếng Việt đạt chuẩn $\ge 30$ video trong `sources.qualified30.json` cho các niche ngách (`anime`, `anh`, `vantay`, `thien`, `mevabe`, `dochai`...).
  0.1. **Cơ chế Multi-source Retry & Replacement (`--max-source-attempts 3` - Case 102) & Inline Auto-Discovery Loop**:
     - Trên remote `origin/main` mới nhất (fb579eb / 42b5aa9), `run_folder` đã bổ sung vòng lặp retry tối đa `--max-source-attempts 3`.
     - Khi một source trong pool bị cạn video (< 30 video), downloader sẽ tự động unlink dọn sạch các file `.mp4`, `.jpg`, `.json` dở dang trong folder, cập nhật các candidate cũ thành `rejection_reason='source_incomplete'`, và thử tiếp source kế tiếp trong pool của cùng niche mà không dừng cả batch.
     - **Bắt buộc Git Pull trước khi phán đoán lỗi**: Khi gặp tình trạng folder thiếu video mà downloader kết thúc sớm, luôn kiểm tra xem máy local đã `git pull` các commit mới nhất (`fb579eb`, `42b5aa9`, `6a3ccd8`) hay chưa.
     - **Vòng lặp tải đến khi đủ $\ge 30$ video**: Nếu danh sách nguồn trong file pool cạn sạch (do các folder trước đã claim hết các niche hẹp), downloader BẮT BUỘC gọi `auto_discover_niche_source()` để search YouTube Shorts mới theo niche, lặp lại việc tìm và probe kênh mới cho đến khi folder đạt $\ge 30$ video mới được dừng.
     - **Kỷ luật Dọn dẹp Tiến trình Trùng (Duplicate Process Killer) khi Relaunch**: Khi user giục "chốt phiên" và "chạy download lại", trước khi gọi launcher `run_download_kibe.py` BẮT BUỘC rà soát `psutil.process_iter` và kill sạch các process download cũ/song song (tránh trường hợp 2 process `download_by_niche.py` cùng chạy gây tranh chấp DB lock, đè candidate và kẹt state `reserved`). Đồng thời reset các folder đang `reserved` dở về `pending` trước khi spawn process mới.
     - Kết hợp với cờ mặc định `--continue-on-insufficient True` (6a3ccd8), batch sẽ lướt qua toàn bộ 640 folder mà không bao giờ bị dừng đột ngột.
  1. **Kiểm tra top niche bị nghẽn `insufficient_pool` (O(1))**:
     `python -c "import sqlite3; conn = sqlite3.connect('C:/CodexRuntime/tiktok-video/state.db'); print(conn.execute('SELECT niche, count(*) FROM folders WHERE status=\"insufficient_pool\" GROUP BY niche ORDER BY count(*) DESC').fetchall())"`
  2. **Bẫy escape ký tự trong Windows batch (`.bat`)**:
     - Khi viết script sinh file `.bat` (như `run_download_kibe_full.bat`), các đường dẫn Windows dạng `D:\CodexRuntime\tiktok-video` hoặc `\venv` dễ bị parse nhầm `\t` thành Tab, `\v` thành Vertical Tab nếu không escape `\\` hoặc dùng forward slash `/`.
     - Hậu quả: CMD văng lỗi `'D:\Taadaa\Tiktok-videoun_download_kibe_full.bat' is not recognized`. Luôn dùng forward slash `/` trong Python/Batch flags (vd: `D:/CodexRuntime/tiktok-video/...`).

  ### Quy trình thay thế nguồn & Reset folder khi nguồn cũ cạn video (Clean-Replace Source)
  Khi một folder bị thiếu video do nguồn cũ cạn Shorts hoặc bị nghẽn `insufficient_pool`, quy trình chuẩn để thay nguồn sạch 100%:
  1. **Dọn sạch đĩa**: Xóa sạch toàn bộ video và file tạm trong thư mục `D:\video goc\<folder_num>`.
  2. **Reset State.db**:
     - `DELETE FROM videos WHERE folder = <folder_num>;`
     - `UPDATE folders SET status = 'pending', source_channel = NULL, video_count = 0, completed_at = NULL WHERE folder_num = <folder_num>;`
  3. **Dọn sạch Ledger claim**: Xóa dòng claim của `<folder_num>` và channel cũ trong toàn bộ file `D:\OneDrive\SharedData\tiktok-video\global-ledger\*.jsonl` để giải phóng namespace.
  4. **Chọn nguồn mới**:
     - Tra cứu trong `sources.qualified30.json` theo niche tương ứng.
     - Kiểm tra đối chiếu với `global-ledger` để đảm bảo kênh chưa bị máy khác claim.
     - Probe nhanh tab `/shorts` qua yt-dlp để xác nhận kênh có $\ge 40$ Shorts còn hoạt động.
  5. **Xoay Proxy & Format Fallback chống 403**:
     - Khi tải YouTube Shorts, nếu gặp HTTP 403 do cookies phiên cũ, xoay proxy di động từ `PROXYgandienthoai.xlsx` (`test.taadaa.click:51xx`).
     - ⚠️ **Bắt buộc URL-encode mật khẩu proxy**: Pass chứa `#` (`%23`), `!` (`%21`) để tránh `yt-dlp` lỗi `Failed to parse proxy URL`.
     - Sử dụng format `18/b[ext=mp4]/best` hoặc `bv*[vcodec^=avc]+ba[ext=m4a]` kèm `-map_metadata -1` để stream MP4 chuẩn tải nhanh và không dính rate-limit.
  6. **Chuẩn hóa & Ghi nhận**:
     - Tải tối thiểu $\ge 30$ video (khuyến nghị 35–42 video).
     - Đánh số thứ tự tuần tự `1.mp4..N.mp4`.
     - Sinh `avatar.jpg` chuẩn từ frame video đầu tiên (crop vuông 512x512).
     - Cập nhật bản ghi `videos` và `folders.status = 'complete'`, `folders.source_channel = <channel_url>`, `folders.video_count = N` trong `state.db`.

  ### ⚠️ Nghẽn cổ chai đơn luồng Whisper (`WHISPER_INFERENCE_LOCK`)
  - Dù chạy `--parallel 32` worker threads tải mạng song song, khâu thẩm định âm thanh Whisper vẫn bị bọc bởi `WHISPER_INFERENCE_LOCK` (để tránh crash CTranslate2 C++ engine). Do đó 32 workers phải xếp hàng chờ lần lượt từng video chạy Whisper. Với các kênh qualified tiếng Việt, ưu tiên nới lỏng đánh giá metadata/audio cache để giải phóng hàng đợi.
- ⚠️ **Lệch số đếm giữa Watchdog và Script đếm MP4**:
  - Script watchdog định kỳ dùng `f.endswith('.mp4')` nên sẽ tính cả các file đang tải dở dạng `.part.mp4`. Khi so sánh với script đếm clean (`not f.endswith('.part.mp4')`), số lượng có thể chênh lệch vài chục file, không phải do video bị mất hay xoá.

## Isolated third-party downloader repo canary (bắt buộc khi so sánh repo mới)

Dùng khi user hỏi có repo mới tải TikTok/YouTube được không, hoặc yêu cầu test repo bên ngoài. Mục tiêu là đánh giá khả năng thay thế, không phải đưa code lạ vào production.

1. Chụp baseline production trước khi clone: `git status --short --branch` và process list cho downloader/render. Giữ nguyên mọi dirty file; không reset, stash, checkout hoặc sửa repo đang dùng.
2. Clone từng repo vào thư mục tạm ngoài repo production; dùng một venv riêng cho từng repo; không cài dependency vào venv production và không đặt `PYTHONPATH` trỏ vào production.
3. Không đọc/ghi `state.db`, workbook, source manifest, global ledger, output render/download, cookie/token/proxy-auth/browser state. Chỉ dùng profile/URL công khai và ghi probe vào thư mục output tạm.
4. Chạy hai canary tách biệt: profile discovery phải trả URL cụ thể dạng `/@handle/video/<id>`; direct URL phải tạo file >1 KiB mà `ffprobe` đọc được container và duration.
5. Phân loại riêng `PROFILE_DISCOVERY_OK`, `PROFILE_DISCOVERY_BLOCKED`, `DIRECT_DOWNLOAD_OK`, `DIRECT_DOWNLOAD_BLOCKED`. Repo chỉ tải được URL cụ thể không được kết luận là thay thế được downloader; replacement candidate phải pass cả discovery và direct canary.
6. Nếu thiếu browser/runtime, chỉ sửa trong môi trường tạm (cài dependency/browser hoặc truyền executable path của browser đã có), chạy lại canary; ghi blocker và cách khắc phục, không biến lỗi setup nhất thời thành quy tắc từ chối repo.
7. Không bypass CAPTCHA/puzzle: gặp challenge thì dừng phân loại `BLOCKED`, không tự giải hoặc né challenge bằng credential/anti-bot workaround.
8. Sau canary, kiểm tra lại production `git status`, process list, và xác nhận probe file nằm ngoài production. Chỉ xem xét tích hợp sau khi có bằng chứng thật từ cả hai canary.

Báo cáo bằng tiếng Việt, ngắn và theo facts: repo/revision, profile candidate count, direct bytes + ffprobe, blocker, bằng chứng isolation. Không báo thành công chỉ vì wrapper/exit code xanh. Chi tiết matrix và evidence snapshot: `references/tiktok-third-party-repo-canary.md`.

## Alternative (CHƯA hoàn chỉnh — ưu tiên cookies)

`scripts/browser_download.py`: Camoufox mở video → bắt response `googlevideo.com/videoplayback` → tải bằng `page.context.request.get()`. ⚠️ URL bắt được là SABR segments (cần Range headers) — tải trực tiếp ra `sabr.malformed_config` (31B). Dùng cookies cho yt-dlp là đường chắc ăn.



## Discovery notes (source_pool_builder.py)

- `--auto-discover` KHÔNG tự qualify: phải thêm `--qualify-videos` mới ghi `qualified_video_count` (0/176 sources khi thiếu flag — nguồn rác lọt pool)

- Tỉ lệ thực: YouTube 120 / IG 55 / TikTok 5 — TikTok extractor broken trong yt-dlp 2026.07.04, IG bị 403 → `PLATFORMS = ("youtube",)`; qualify xong 70 sources ≥45 video (67 YT)

- `max_folders_per_channel=1` → ~70 folder hoàn thành tối đa

- **`target_counts()` mặc định 50/25/25 (TikTok/IG/YT)** → discovery dừng khi đạt 120 YT dù cần 480: sửa thành YouTube 100% (`{"tiktok":0,"instagram":0,"youtube":total}`) + `--min-sources-per-platform 0` (không thì INSUFFICIENT vì tiktok=0) → discovery tiếp tìm tới 454 YT sources

- **Qualify cần `--cookies-file`** (probe từng video không cookies → "not available" hàng loạt = đếm thiếu). source_pool_builder CHỈ có `--cookies-from-browser` (vô dụng với Chromium App-Bound) → đã thêm flag `--cookies-file`; probe dùng `yt_options(args)` import từ download_by_niche nên tự kế thừa

- `youtube_profile` regex phải là `@[\w.-]+` (handle Unicode tiếng Việt có dấu bị chặn bởi `[A-Za-z0-9._-]+`)

- Bỏ `@vtv24` (kênh nhà nước — user không muốn dùng)



## Operational pause/resume and resource-safe recovery

When the user asks to pause or resume download/render jobs on a live farm machine:

1. Identify the exact managed process/session by command line (`download_by_niche.py`, `tik3_multi_batch.py`, `run_tik4_random_render.ps1`) before acting. Do not stop unrelated ADB, proxy, gateway, registration, or feed processes.
2. Pause both the tracked background session and any child process it spawned. Verify with a fresh process-list query that no matching download/render/ffmpeg child remains. A session marked killed is not sufficient proof by itself.
3. Resume download with the original `state.db`, output root, global ledger, and `--ledger-machine-id`; do not reset state or start a second duplicate downloader. Preserve `--continue-on-insufficient` and the configured proxy/cookie isolation flags.
4. Resume render with the project launcher and its resume/idempotency flags. If the user requests one worker, pass `-Parallel 1`; do not substitute a generic multi-batch command with a different workbook or source mapping.
5. After launching, poll the session and inspect command-line/process evidence. Report only verified status. Treat YouTube 403/unavailable/sign-in messages as per-video download failures unless the process itself exits or the state DB shows a fatal batch error.
6. If download and render run concurrently, keep their resource controls explicit and independent; pausing one must not silently stop or restart the other.

For session-specific pause/resume evidence and the PowerShell quoting-safe launch pattern, see `references/pause-resume-and-resource-checks.md`.

## State / source-pool recovery and canary gate (bắt buộc trước batch)

Khi log có `INSUFFICIENT_POOL`, `This video is not available`, hoặc `does not have a shorts tab`, không kết luận downloader hỏng và không chạy lại batch 20 worker ngay. Tách 4 lớp: (1) source discovery/listing, (2) cached candidate validation, (3) proxy/download, (4) state/ledger reservation.

1. **Đọc state trước khi sửa nguồn**: kiểm tra `folders` (niche/platform/source/status), đếm `videos` theo status và `rejection_reason`, đối chiếu số MP4 thật trên đĩa. `RECOVERED_INTERRUPTED` là recovery của state cũ, không phải số video mới.
2. **Resume cache trước khi crawl lại**: load candidate `discovered` đã có đúng `source_channel + niche + platform`; hydrate metadata bằng yt-dlp trước khi queue. Loại sớm URL unavailable và `duration > 300`; candidate có `duration=None` không được coi là hợp lệ nếu chưa probe. Việc này tránh một playlist `/videos` dài hoặc entry chết làm pool tụt về 0.
3. **Chuẩn hóa định danh**: so sánh `source_channel` không phân biệt hoa/thường (`lower(...)`), và giữ platform nhất quán. Nếu folder ghi TikTok nhưng source/candidate là YouTube, đó là state mismatch phải sửa trước khi đánh giá pool.
4. **Chuẩn hóa proxy tại boundary**: workbook có thể lưu `http://host:port:user:pass`; chuyển thành URL chuẩn `http://user:encoded_pass@host:port` cho yt-dlp (đặc biệt encode `#`, `!`, `@`). Đảm bảo `_worker_proxy()` cũng gọi cùng formatter; chỉ sửa parser đầu vào là chưa đủ.
5. **Ledger**: claim của chính machine/folder chưa hoàn tất phải resumable; claim của machine khác vẫn phải skip. Không xóa/reset ledger hoặc state để làm pool “đẹp”.
6. **Canary gate**: chạy đúng 1 folder + 1 source + `--parallel 1`, giữ nguyên state/output/ledger production, nhưng không chạy batch rộng. Chỉ pass khi có MP4 mới non-zero thực tế, DB ghi `downloaded`, và sau resume/finish folder chuyển `complete`; wrapper exit code 0 một mình không phải bằng chứng. Nếu phải dừng canary giữa chừng, chạy một lần resume để chuyển mọi `downloading` thành trạng thái cuối trước khi báo cáo.
7. **Chỉ sau canary mới scale**: xác nhận không có process downloader trùng, rồi mới dùng batch launcher. Không kill một process đang tải candidate cuối chỉ vì đã thấy đủ file trên đĩa; nếu cần dừng, chờ/khởi động resume và kiểm tra `folders.status`, `video_count`, file count lại.

Evidence tối thiểu và mẫu truy vấn/checklist: `references/source-pool-state-reconciliation.md`.

## Shared-output folder isolation (bắt buộc)

- **Một output folder chỉ được thuộc một source/platform/niche.** Không dùng `folder_num` từ một state DB rồi ghi vào `D:\video goc\<folder_num>` nếu folder đó đã có MP4 hoặc đang được quản lý bởi một DB khác.
- **Hai state DB độc lập không tạo namespace độc lập trên cùng output root.** Trước khi reserve, reconcile mọi downloader DB có thể trỏ tới cùng output root; coi `(output_root, folder_num)` là shared resource.
- **Định dạng tên là bằng chứng nguồn, không phải thứ để tự động renumber:** `1.mp4..N.mp4` là batch numeric; `[title] [youtube_id].mp4` là batch title-based. Đối chiếu `output_path`, `source_channel`, `platform`, `niche` trước khi move/rename.
- Khi batch title-based đủ 30 video, cấp một folder số mới chưa từng dùng, move nguyên batch (kèm avatar/manifest nếu có), rồi cập nhật state DB `folder`, `output_path`, `video_count=30`, `status=complete`. Không trộn phần thiếu với source khác.
- Sau khi sửa, nếu user đã yêu cầu chạy thì phải chạy ngay đúng một production process; không dừng ở báo cáo “đã sửa”, và không lấy canary của folder khác làm bằng chứng cho folder đang được hỏi.
- Nếu dirty-tree/bootstrap gate chặn thì báo blocker ngắn gọn, không reset/stash/commit tự ý; nhưng vẫn phải phân biệt rõ blocker code với kết quả runtime.

Chi tiết inventory, collision detection và move an toàn: `references/folder-isolation-and-reconciliation.md`.
Chi tiết cross-folder channel deduplication & persistent claims cho gai xinh pipelines (`smart_gaixinh_distributor.py`, `download_gaixinh_pipeline.py`): `references/cross-folder-channel-dedup-and-claims.md`.

### Deduplication kênh chéo folder & Persistent Claims (GaiXinh Pipelines)
- **Central claims registry**: `data/gaixinh_channel_claims.json` lưu ánh xạ kênh -> folder đã gán, ngăn tình trạng phân bổ trùng lặp kênh giữa các folder khác nhau.
- **Folder descriptors**: Mỗi output folder lưu `D:\video goc\<folder_num>\channel_info.json` để xác minh tại chỗ và hỗ trợ auto-reconciliation khi khởi động.
- **Clean-old release**: Khi chạy với `--clean-old`, phải giải phóng claim của folder đó trong central registry và xóa file `channel_info.json`.
- **Kỷ luật tool calls khi can thiệp downloader**: Tránh đọc tuần tự toàn bộ file lớn bằng `read_file` (dễ cạn kiệt budget 15-20 iterations); tập trung vào các điểm gán kênh và viết unit test độc lập.

## Pitfalls

- **Camoufox + proxy bắt buộc dạng dict riêng**: `Camoufox(headless=False, proxy={"server": "http://host:port", "username": "...", "password": "..."})` hoặc `browser.new_context(proxy={...})`. NHÉT user:pass@ vào server URL (kể cả URL-encode) → `NS_ERROR_PROXY_CONNECTION_REFUSED` dù curl qua proxy vẫn OK. Pass chứa `#` phải URL-encode (`%23`) nếu ghép URL. Chẩn đoán nhanh: `curl -x http://user:pass@host:port https://api.ipify.org` — curl OK + Camoufox REFUSED = lỗi cú pháp proxy trong Camoufox, không phải proxy chết.
- **Camoufox headless bị Cloudflare "Just a moment"**, headful (trên Linux dùng `xvfb-run -a`) qua được — nhưng chỉ khi **IP dân cư thật**; IP datacenter/proxy mobile farm bị chặn bất kể browser/fingerprint.
- Chrome/Edge cookies KHÔNG đọc được (Chromium App-Bound/DPAPI — yt-dlp issue #7271); Firefox profile có nhưng không có YouTube session → dùng Camoufox

- deno JS runtime: `pip install deno` + `--js-runtimes "deno:<venv>/Scripts/deno.exe"` + `--extractor-args "youtube:jsc=deno"` — vẫn fail "n challenge solving failed" nếu thiếu solver; cookies là chìa khóa

- Probe hàng loạt (1 request/video liên tục) vẫn bị chặn dù có cookies — cookies tươi + request lẻ thì OK; chạy dài cần refresh cookies giữa chừng

- MobiProxy panel giới hạn kết nối đồng thời: test SONG SONG toàn pool (8 worker × nhiều proxy cùng lúc) thấy 407 auth fail dù proxy sống (uptime 92h) — thử lại proxy ĐƠN LẺ OK, download thật (mỗi worker 1 proxy riêng) không bị 407 → đừng kết luận "proxy chết" khi thấy 407 từ test song song

- ⚠️ **Lỗi yt-dlp `Video unavailable` (visionos player API) & Rate-limit 1 giờ**:
  - `yt-dlp` bản mới (2026.08+) mặc định dùng `visionos player API` dẫn đến văng lỗi `Video unavailable` giả.
  - **Khắc phục**: Thêm `"extractor_args": {"youtube": {"player_client": ["android"]}}` vào `ydl_opts` để ép dùng Android player API.
  - Khi IP bị YouTube rate-limit ("rate-limited by YouTube for up to an hour"), xoay qua cổng **MikroTik LAN PPPoE proxy pool (`192.168.110.2:10001..10035` với auth `admin@1:admin@1`)** để lấy IP dân cư nội bộ độ trễ 0.01s, tốc độ tải 10–26 MB/s.
  - Cài đặt `deno` (`pip install deno`) để cung cấp JS runtime tự động cho yt-dlp.
  - Chi tiết xem: `references/youtube-android-client-and-mikrotik-pool-fix.md`.
- ⚠️ **Lỗi C++ `brotli` vs `brotlicffi` trên Windows**: Gói `brotli 1.2.0` gốc C++ bị lỗi memory allocation (`ERROR: brotli: unable to allocate memory` dẫn tới exit code 127/139) khi xử lý giải nén HTTP stream trên nhiều worker song song. Khắc phục: `pip install brotlicffi` và `pip uninstall -y brotli`.
- ⚠️ **Lỗi Windows File Lock khi ghi Cache (`[WinError 5] Access is denied`)**: Khi đa luồng cùng ghi file cache (như `audio_lang_cache.json`), không dùng cơ chế ghi file `.part.json` rồi `replace()` vì Windows sẽ lock file gây `Access is denied`. Phải dùng `threading.Lock()` ghi trực tiếp vào file đích.
- ⚠️ **CTranslate2 / Faster-Whisper multi-thread Segfault (C++ crash exit code 127/139)**: 
  - Khởi tạo mỗi worker 1 instance `WhisperModel` (`WHISPER_LOCAL = threading.local()`) chạy đồng thời nhiều thread CPU sẽ làm CTranslate2 C++ engine bị crash bộ nhớ luồng (`transcribe.py encode`).
  - Khắc phục: Khởi tạo **1 model toàn cục duy nhất** (`WHISPER_GLOBAL_MODEL`) và bọc đoạn gọi `transcribe()` bằng `WHISPER_INFERENCE_LOCK = threading.Lock()`. Khi tải hàng loạt từ các kênh tiếng Việt đã qualify trong `sources.qualified30.json`, có thể bypass/tắt bước Whisper để tối ưu tốc độ và triệt tiêu 100% rủi ro memory leak / C++ crash.
- ⚠️ **Memory leak & Out of Virtual Memory khi chạy batch dài (20 workers)**: Chạy `download_by_niche.py` liên tục qua hàng trăm folder có thể bị tích tụ heap/buffer làm phình Private Memory (Virtual Memory) lên đến >150 GB. Khi Commit Charge cạn kiệt, Windows sẽ kích hoạt popup `Out of Virtual Memory` và khiến các tiến trình khác (như `adb.exe`, `conhost.exe`) không khởi tạo được DLL → văng popup lỗi `0xc0000142` (STATUS_DLL_INIT_FAILED).
  - **Hiệu ứng domino lên OneDrive**: Tiến trình đồng bộ ngầm `OneDrive.exe` khi cạn RAM sẽ bị corrupt/drop session auth trong bộ nhớ $\rightarrow$ tự động restart với switch `/convergenceFre /email:...` làm văng phiên đăng nhập (bắt user login lại), đồng thời quét lại các mount point cũ (ví dụ SharePoint Online `OneDrive on SPO`) và bắn popup báo không tìm thấy thư mục.
  - **Chẩn đoán nhanh khi thấy popup 0xc0000142 / OneDrive văng**: Chạy PowerShell kiểm tra top process ngốn Virtual Memory:
    `Get-Process | Sort-Object -Property PrivateMemorySize64 -Descending | Select-Object -First 10 ProcessName, Id, @{N='PrivMem(MB)';E={[math]::round($_.PrivateMemorySize64/1MB,2)}}`
  - **Xử lý**: Kill process `download_by_niche.py` bị leak RAM (`Stop-Process -Id <PID> -Force`), Virtual Memory sẽ giải phóng ngay lập tức. Sau đó đăng nhập lại tài khoản OneDrive và giữ nguyên thư mục `D:\OneDrive`.

- ⚠️ **Resume crash: `FileExistsError: numeric target is not part of the rename set`** — folder chạy lại (resume) trong khi đĩa còn dải file số `1.mp4..N.mp4` của run cũ (state.db đã trỏ path dài `[youtube_xxx].mp4` từ lần renumber trước; file số cũ không còn row nào tham chiếu) → `renumber_mp4_files()` đụng target số tồn tại ngoài rename set → exception thoát khỏi `run_folder` → **chết cả batch exit 1 dù có `--continue-on-insufficient`** (cờ này chỉ chặn INSUFFICIENT_POOL, không chặn exception).
  - Fix (ee654f6): `stale_orphan_numeric_mp4s()` = file tên số KHÔNG trong rename set hiện tại và mtime > 24h (rác run cũ) + `perform_renumber()` dọn rác TRƯỚC conflict detection; vẫn raise khi conflict thật (2 run đè nhau). Regression: `tests/test_renumber_stale_numeric.py` (6 test xanh).
  - Chẩn đoán nhanh: đếm mp4 trên đĩa vs `SELECT output_path FROM videos WHERE folder=? AND status='downloaded'` — file số trên đĩa không DB trỏ tới + mtime cũ = stale an toàn dọn; file số MỚI (cùng đợt đang chạy) = đang xử lý, KHÔNG đụng.
  - Vị trí fix và chạy lại: `--continue-on-insufficient` KHÔNG cứu được batch khi exception; sau khi sửa code phải chạy lại lệnh batch đầy đủ flags (đã lưu trong `references/worker-isolation-ledger.md`).
- Chi tiết worker isolation + ledger + backfill: `references/worker-isolation-ledger.md`
# Điều phối Tải Gái Xinh (VN + Douyin), Khắc phục Bot-Check & Vận hành Remote Admin

## 1. Quy tắc Tinh gọn Báo cáo Watchdog (User Invariant 2026-09-30 & 2026-10-03)
- **Yêu cầu từ User**: *"Còn download máy kibe xong thì k báo nữa"*.
- **Kỷ luật hiển thị**:
  - Khi kho video gốc của một cụm farm (Kibe hoặc Admin) đã hoàn thành 100% chuẩn mới ($\ge 40$ video cho cả 640/640 folder nguồn, target 45) và không có tiến trình download nào đang chạy ngầm (`is_download_running() == False`):
  - **TUYỆT ĐỐI KHÔNG hiển thị phần "1. Video gốc"** trong tin nhắn báo cáo định kỳ.
  - Watchdog tự động đổi tiêu đề thành `BÁO CÁO TIẾN ĐỘ [FARM] (RENDER)` và chỉ hiển thị tập trung danh sách tiến độ Render Tik1..Tik8.
  - Tránh làm rác kênh chat hoặc Farm Alert bằng các thông tin đã hoàn thành.

---

## 2. Khắc phục YouTube Bot-Check trong GaiXinh Fallback Pipeline
- **Hiện tượng**: Trong script `scripts/download_gaixinh_pipeline.py`, sau khi quét hết các kênh TikTok trong manifest mà folder chưa đủ `min_videos` (40 video), script kích hoạt fallback tìm kiếm Shorts YouTube theo từ khóa (`ytsearch30:gái xinh douyin shorts`, `dance gái xinh shorts`...). Lúc này yt-dlp văng lỗi:
  ```text
  ERROR: [youtube] <id>: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication.
  ```
- **Nguyên nhân**: YouTube áp dụng bot-check yêu cầu phiên cookies đăng nhập thật, không cho phép client anonymous tải stream.
- **Giải pháp O(1)**:
  - Sử dụng file Netscape cookies có sẵn tại `D:/CodexRuntime/tiktok-video/youtube-cookies.txt`.
  - Cấu hình `cookiefile` vào `ydl_opts` tại cả 3 vị trí:
    1. `extract_candidate_videos`
    2. `extract_fallback_search_videos`
    3. `download_single_video`
  - Code chuẩn:
    ```python
    cookie_path = Path(r"D:/CodexRuntime/tiktok-video/youtube-cookies.txt")
    if cookie_path.exists():
        ydl_opts["cookiefile"] = str(cookie_path)
    ```
  - Kết quả kiểm chứng: Tốc độ tải đạt 10–20 MB/s, 100% video vượt qua bot-check mà không cần can thiệp trình duyệt thủ công.

---

## 3. Mở rộng Tập Từ khóa Fallback Gái Xinh (VN + Douyin)
- **Vấn đề cạn kiệt nguồn**: 5 từ khóa mặc định chỉ cho ra ~150 video. Với cơ chế `seen_ids` dedupe toàn đợt chạy, sau khi tải 3–4 folder thì các từ khóa này sẽ cạn sạch, dẫn tới các folder tiếp theo bị lỗi `Video unavailable` hoặc thiếu video.
- **Tập từ khóa chuẩn mở rộng ($\ge 15$ keywords)**:
  ```python
  DEFAULT_FALLBACK_KEYWORDS = [
      "gái xinh douyin shorts",
      "gái xinh tiktok shorts",
      "dance gái xinh shorts",
      "douyin visual shorts",
      "cô gái trung quốc shorts",
      "gái xinh việt nam shorts",
      "hot girl tiktok việt nam",
      "gái xinh nhảy tik tok",
      "tổng hợp gái xinh tik tok",
      "nữ sinh việt nam shorts",
      "áo dài việt nam shorts",
      "gái xinh nhảy trend tiktok",
      "douyin hot girl dance",
      "douyin beauty shorts",
      "douyin dance shorts",
      "gái xinh nhảy bốc shorts",
      "mỹ nữ douyin shorts",
      "visual gái việt shorts",
  ]
  ```

---

## 4. Điều phối Remote Batch Render & Download sang Máy Admin qua SSH
- **Kiến trúc**: Kibe đóng vai trò Master điều phối trực tiếp Admin qua SSH (`admin-farm` - `192.168.110.119`).
- **Khắc phục lỗi mã hóa Unicode cp1252 trên Windows Admin**:
  - Môi trường CMD/PowerShell trên Windows Admin mặc định là cp1252. Khi Python print ký tự tiếng Việt có dấu (`\u1ede`), tiến trình sẽ văng lỗi `UnicodeEncodeError: 'charmap' codec can't encode character...`.
  - Khắc phục ở đầu mỗi script chạy trên Admin:
    ```python
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ```
    Đồng thời truyền `env["PYTHONIOENCODING"] = "utf-8"` trong các subprocess call.

- **Chuỗi Render cuốn chiếu Admin (`admin_render_chain.py`)**:
  - Dùng khi Admin cần chạy tiếp các slot từ Tik1 đến Tik8 (chuẩn 45 clip):
    ```bash
    python D:/Taadaa/Tiktok-video/scripts/admin_render_chain.py --start-from 1 --skip-wait-tik2
    ```
  - **Mở rộng bao phủ đủ 8 Tik (Tik1..Tik8)**:
    - Trong `scripts/admin_render_chain.py`, mảng `STEPS` bắt buộc khai báo đủ từ Tik1 đến Tik8:
      ```python
      STEPS = [
          (1, REPO / "run_tik1_random_render.ps1"),
          (2, REPO / "run_tik2_random_render.ps1"),
          (3, REPO / "run_tik3_random_render.ps1"),
          (4, REPO / "run_tik4_random_render.ps1"),
          (5, REPO / "run_tik5_random_render.ps1"),
          (6, REPO / "run_tik6_random_render.ps1"),
          (7, REPO / "run_tik7_random_render.ps1"),
          (8, REPO / "run_tik8_random_render.ps1"),
      ]
      ```
    - Đồng thời `--start-from` choices phải là `[1, 2, 3, 4, 5, 6, 7, 8]` (default `1`).
  - **BẪY THAM SỐ `--parallel` VÀ LỖI CRASH TRÊN ADMIN**:
    - **Triệu chứng crash**: `admin_render_chain.py: error: unrecognized arguments: --parallel 1`.
    - **Nguyên nhân**: File launcher `.bat` truyền `--parallel 1` nhưng script `admin_render_chain.py` trên máy Admin chưa khai báo `--parallel` trong `build_arg_parser()`. (Lưu ý: hàm `run_step` trong supervisor vốn đã hardcode `"-Parallel", "1"` khi gọi PowerShell).
    - **Cách xử lý**: Bắt buộc thêm `parser.add_argument("--parallel", type=int, default=1, ...)` vào `admin_render_chain.py` VÀ dùng lệnh SCP đồng bộ script sang Admin:
      ```bash
      scp D:/Taadaa/Tiktok-video/scripts/admin_render_chain.py admin-farm:D:/Taadaa/Tiktok-video/scripts/admin_render_chain.py
      ```
  - **KỶ LUẬT THỰC THI CHỦ ĐỘNG (USER INVARIANT - CẤM ĐẨY VIỆC CHO USER)**:
    - Khi User yêu cầu: *"chạy cho xong hết admin vs yêu cầu folder đạt chuẩn đi"*, Agent **BẮT BUỘC PHẢI TỰ ĐỘNG KÍCH HOẠT THỰC THI NGẦM** qua SSH/WMIC Session 0.
    - **CẤM TUYỆT ĐỐI** đưa hướng dẫn dạng: *"Anh chỉ cần double-click...", "Anh chỉ cần mở PowerShell chạy..."*. Nếu bị chặn guard (hết dispatch budget, write budget), chuyển ngay sang L3 BLOCKED kèm bằng chứng error log thật, không được giả vờ hoàn tất hay hướng dẫn User làm thay Agent.
  - **Lưu ý quan trọng (BẪY OPENSSH WINDOWS & GIẢI PHÁP DETACHED 100%)**:
    - Khi SSH vào Windows Admin, nếu chỉ dùng `Start-Process` thông thường, OpenSSH server trên Windows có thể gắn tiến trình con vào Job Object của phiên SSH; khi ngắt kết nối SSH hoặc tắt terminal, toàn bộ tiến trình con có nguy cơ bị đóng băng hoặc tắt ngang.
    - **Giải pháp chuẩn Session 0 qua WMI**:
      Tạo hoặc gọi file `run_admin_render_chain.bat` (đặt sẵn tại `D:\Taadaa\Tiktok-video\run_admin_render_chain.bat`), sau đó kích hoạt detached qua WMI:
      ```bash
      ssh admin-farm "wmic process call create \"cmd.exe /c D:\\Taadaa\\Tiktok-video\\run_admin_render_chain.bat\""
      ```
      Tiến trình sẽ chạy độc lập hoàn toàn trong Session 0, bất tử trước việc ngắt kết nối SSH hay tắt máy client.
    - **Nội dung chuẩn của `run_admin_render_chain.bat`**:
      ```batch
      @echo off
      setlocal
      set PYTHONUTF8=1
      set PYTHONIOENCODING=utf-8
      set TIKTOK_VIDEO_RUNTIME_ROOT=D:\CodexRuntime\tiktok-video
      set PATH=C:\Users\Admin\AppData\Local\hermes\hermes-agent\venv\Scripts;%PATH%
      cd /d D:\Taadaa\Tiktok-video
      "C:\Users\Admin\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" -u scripts\admin_render_chain.py --skip-wait-tik2 --start-from 5 > "D:\CodexRuntime\tiktok-video\batch-runs\admin_render_chain.stdout.log" 2>&1
      ```

- **Quy tắc Báo cáo Tập trung DUY NHẤT qua Bot Kibe (User Invariant 2026-10-01)**:
  - User đã dẹp hẳn Bot Admin (`@taadaa_admin_hermes_bot`). TUYỆT ĐỐI CẤM cấu hình cronjob Admin gửi tin nhắn Telegram hay add bot Admin vào Farm Alerts.
  - Khi User hỏi: *"Sao không báo farm admin?"* $\rightarrow$ **Ý của User là: Tại sao tin nhắn báo cáo của Bot Kibe lại thiếu số liệu cụm Farm Admin**, TUYỆT ĐỐI KHÔNG ĐƯỢC suy diễn là bật bot bên máy Admin hay kiểm tra cron gửi tin bên máy Admin!
  - Toàn bộ cronjobs trên máy Admin chỉ được phép chạy ở chế độ `deliver: "local"` hoặc để `enabled: false`.
  - **DUY NHẤT Bot Kibe** (`@Taadaa_hermes_sever_bot`) tổng hợp báo cáo 2 cụm (Kibe M1-80 & Admin M201-280) gửi về kênh Farm Alerts (`-5373649734`).
  - Script watchdog trên Kibe (`farm_render_download_watchdog.py`) tự động query Admin LAN qua SSH (timeout 5s), đồng thời lưu và fallback đọc cache OneDrive (`D:\OneDrive\TaadaaData\admin\last_render_stats.json`) khi mạng LAN gián đoạn.
  - Hàm `is_render_running()` trong watchdog bắt buộc phải bắt cả chuỗi `"admin_render_chain"` ngoài `"random_batch_render.py"` và `"ffmpeg"` để không bị nhảy sai trạng thái `⚪ Đang dừng` trong khoảng thời gian gối đầu giữa các video/folder.

- **Cào video Gái Xinh bù kho Admin (`run_admin_gaixinh_downloader.py`)**:
  - **Yêu cầu tiền đề**: Trước khi chạy trên Admin, bắt buộc SCP đồng bộ 5 tài nguyên:
    1. `D:/Taadaa/Tiktok-video/scripts/download_gaixinh_pipeline.py` (đã có cookiefile và 18 keywords)
    2. `D:/Taadaa/Tiktok-video/data/source_manifest_gaixinh.jsonl`
    3. `D:/Taadaa/Tiktok-video/data/douyin_hot_girls.json`
    4. `C:/Users/Admin/AppData/Local/hermes/evidence/douyin_test/cookie_string.txt` (cookie Douyin)
    5. `D:/CodexRuntime/tiktok-video/youtube-cookies.txt` (cookie YouTube)
  - Khởi chạy nền qua PowerShell:
    ```powershell
    Start-Process -FilePath python -ArgumentList @("D:/Taadaa/Tiktok-video/scripts/run_admin_gaixinh_downloader.py") -WorkingDirectory "D:/Taadaa/Tiktok-video" -WindowStyle Hidden
    ```
  - Log theo dõi tại: `D:/CodexRuntime/tiktok-video/download_gaixinh_admin.log`.

---

## 5. Quy tắc Render Bổ sung Tik7 (Slot 7)
- **Tiền điều kiện**: Mỗi thư mục video gốc bắt buộc phải có `avatar.jpg` trước khi chạy `random_batch_render.py` (nếu thiếu có thể copy avatar hợp lệ từ folder mẫu).
- **Quy tắc mapping tham số**:
  - `Slot 7` (1-indexed) tương ứng tham số `--slot 6` (0-indexed).
  - `Machine M` (1-indexed) tương ứng tham số `--machine-id M - 1` (0-indexed).
  - Run ID chuẩn: `--run-id "kibe-m{M}-slot7-f{Folder}"`.

---

## 6. Chẩn đoán & Phục hồi Chuỗi Render Admin Bị Dừng Ngang
- **Hiện tượng**:
  - Watchdog báo trạng thái render của Admin: `⚪ Đang dừng`.
  - Quét `psutil` trên Admin không còn tiến trình `python.exe` hay `ffmpeg.exe` nào liên quan tới batch render.
- **Quy trình kiểm tra O(1) chuẩn hóa**:
  1. **Đọc log giám sát cuối cùng**:
     - Đọc 30 dòng cuối `D:\CodexRuntime\tiktok-video\batch-runs\admin_render_chain.log` và `admin_render_chain.stdout.log` để xác định bước và máy vừa hoàn thành.
     - **Dấu hiệu nhận diện nguyên nhân dừng**:
       - *Dừng tự nhiên / hoàn tất*: Có dòng `All requested render chain steps completed successfully.`
       - *Lỗi crash script*: Có traceback Python hoặc `TikX failed with exit code N`.
       - *Dừng khẩn cấp do Tree-Kill / User tắt (ví dụ để chơi game)*: Log bị cụt ngang giữa chừng một task (ví dụ dừng ở `PROGRESS: 15/45 tasks`) mà không có exit code hay traceback. Tra cứu lại `session_search(query="admin_render_chain")` để xác nhận bối cảnh phiên trước.
  2. **Kiểm tra batch log chi tiết**:
     - Mở thư mục batch mới nhất trong `D:\CodexRuntime\tiktok-video\batch-runs\tik*-random-admin-*\launcher.log`.
     - Xác định machine/folder cuối cùng hoàn thành (ví dụ: `M272 output 573: 45 MP4`).
  3. **Đối soát target workbook `Tik*.xlsx`, cache OneDrive & Live Query O(1)**:
     - Lệnh trích xuất Live stats của Admin (`is_dl`, `is_rd`, `src_ge45`, `tik_stats` Tik1..Tik8) trực tiếp từ Kibe:
       ```bash
       python -c "import sys; sys.path.append(r'C:\Users\Kibe\AppData\Local\hermes\scripts'); import farm_render_download_watchdog as f; data, status = f.fetch_admin_stats_remote(); print('Status:', status); print(data)"
       ```
     - Hoặc đọc cache OneDrive `D:\OneDrive\TaadaaData\admin\last_render_stats.json` để nắm ngay số lượng folder và clip của Tik1..Tik8.
     - Quét các folder còn thiếu (`0 MP4` hoặc `< 45 MP4`) trong dải `201..280`.
     - Kiểm tra kho nguồn `D:\video goc may 2\<source>` tương ứng xem có đủ $\ge 40$ video không (nếu `< 40`, script sẽ tự động SKIP).
  4. **Dọn rác 0-byte tại output folder của máy đang dở dang**:
     - Nếu tiến trình bị tree-kill giữa chừng, kiểm tra folder output của máy đang chạy (ví dụ `D:\TIKTOK-videonuoinick-admin\<folder>`) và xóa các file MP4 0-byte:
       ```powershell
       ssh admin-farm "powershell -Command \"Get-ChildItem -Path 'D:\TIKTOK-videonuoinick-admin\<folder>' -Filter *.mp4 | Where-Object { \$_.Length -eq 0 } | Remove-Item -Force\""
       ```
  5. **Đồng bộ file launcher an toàn (Kibe -> Admin qua SCP)**:
     - Khi cần đổi tham số (ví dụ `--start-from 8`, `--parallel 1`), **TUYỆT ĐỐI KHÔNG** dùng lệnh inline PowerShell dài qua SSH dễ gãy quoting/backtick.
     - **Quy trình chuẩn**: Sửa file `run_admin_render_chain.bat` tại máy Kibe (`D:\Taadaa\Tiktok-video\run_admin_render_chain.bat`), sau đó SCP sang Admin:
       ```bash
       scp -o ConnectTimeout=5 "D:/Taadaa/Tiktok-video/run_admin_render_chain.bat" admin-farm:"D:/Taadaa/Tiktok-video/run_admin_render_chain.bat"
       ```
  6. **Kích hoạt lại chuỗi render nền (Detached Session 0 qua WMI)**:
     - Tuyệt đối không chạy lệnh foreground trực tiếp trên terminal SSH hoặc Start-Process nếu có nguy cơ ngắt phiên kết nối làm chết process.
     - Khởi chạy nền qua WMI Create để tiến trình chạy trong Session 0 bất tử trên máy Admin:
       ```bash
       ssh admin-farm "wmic process call create \"cmd.exe /c D:\\Taadaa\\Tiktok-video\\run_admin_render_chain.bat\""
       ```
     - Sau khi kích hoạt, kiểm tra lại bằng `tasklist /FI "IMAGENAME eq python.exe"` và theo dõi log `admin_render_chain.log`. Kiểm chứng watchdog Kibe chuyển sang `🟢 Đang chạy`.

---

## 7. Dừng Khẩn Cấp hoặc Điều Chỉnh Worker Render Admin (Bẫy ffmpeg Respawn & Tree-Kill)
- **Hiện tượng & Bẫy ffmpeg Respawn**:
  - Khi User tắt `ffmpeg.exe` trong Windows Task Manager (đặc biệt khi đang chơi game hoặc cần giải phóng CPU khẩn cấp), `ffmpeg.exe` **lập tức tự động bật lại**.
  - **Nguyên nhân**: `ffmpeg.exe` chỉ là tiến trình con do vòng lặp của script cha (`admin_render_chain.py` $\rightarrow$ `run_tik*.ps1` $\rightarrow$ `random_batch_render.py`) gọi ra. Khi `ffmpeg.exe` bị kill, Python coi như video đó hoàn tất/lỗi và lập tức spawn ffmpeg cho video tiếp theo trong danh sách. Hơn nữa tiến trình chạy Session 0 (WMI) nên Task Manager thường của User không dọn được cả cây.
- **Quy trình Dừng Triệt Để (Tree-Kill O(1))**:
  1. **Tree-Kill toàn bộ cây tiến trình**:
     ```bash
     ssh admin-farm "taskkill /F /T /IM ffmpeg.exe 2>nul & powershell -Command \"Get-CimInstance Win32_Process -Filter \\\"name = 'python.exe' or name = 'cmd.exe' or name = 'powershell.exe'\\\" | Where-Object { \$_.CommandLine -like '*admin_render_chain*' -or \$_.CommandLine -like '*random_batch_render*' -or \$_.CommandLine -like '*run_tik*' -or \$_.CommandLine -like '*run_admin_render_chain*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }\""
     ```
     Hoặc nếu có PID gốc cmd/wmi Session 0: `taskkill /F /T /PID <root_pid>`.
  2. **Dọn rác 0-byte tránh corrupt output**:
     Khi ffmpeg bị kill ngang, file MP4 đang render dở sẽ có dung lượng 0-byte hoặc bị thiếu header moov atom. Bắt buộc xóa các file 0-byte tại output folder trước khi chạy lại:
     ```powershell
     Get-ChildItem -Path "D:\TIKTOK-videonuoinick-admin\*" -Filter *.mp4 -Recurse | Where-Object { $_.Length -eq 0 } | Remove-Item -Force
     ```
  3. **Hạ worker (ví dụ giảm từ 2 xuống 1 worker) hoặc Khôi phục 2 workers**:
     - Sửa cấu hình `--parallel 1` (khi cần nhẹ máy/user chơi game) hoặc `--parallel 2` (khi user yêu cầu "chạy worker 2 nốt": `--parallel 2 --start-from 8`) trong file launcher `D:\Taadaa\Tiktok-video\run_admin_render_chain.bat`.
     - SCP sang Admin và kích hoạt detached Session 0 qua WMI:
       ```bash
       scp -o ConnectTimeout=5 "D:/Taadaa/Tiktok-video/run_admin_render_chain.bat" admin-farm:"D:/Taadaa/Tiktok-video/run_admin_render_chain.bat"
       ssh admin-farm "wmic process call create \"cmd.exe /c D:\\Taadaa\\Tiktok-video\\run_admin_render_chain.bat\""
       ```
     - Xác minh: Kiểm tra `Get-Process -Name ffmpeg` thấy đúng 2 PIDs ffmpeg đang tích lũy CPU.

---

## 8. Xử Lý Bù 1 Clip Cho Folder Thiếu Đạt Ngưỡng Watchdog ($\ge 30$ clip)
- **Hiện tượng**: Watchdog báo một Tik bị thiếu lẻ 1 folder (ví dụ `Tik5: 79/80 [98.8%]`), căn nguyên thường do folder ngẫu nhiên dừng ở 29 clip sau thao tác swap folder/batch cũ (`start-seq` và số lượng video chia lệch).
- **Quy trình vá O(1) không cần render lại cả folder**:
  1. **Xác định folder thiếu**: Chạy script one-liner O(1) đối soát các folder `(m - 1) * 8 + slot` của Tik đó để tìm folder có `< 30` MP4.
  2. **Tạo danh sách 1 clip nguồn**: Tạo file tạm `C:\Users\Kibe\AppData\Local\Temp\list_patch.txt` chứa đường dẫn 1 video nguồn chưa render từ `D:\video goc\<folder>\<next>.mp4`.
  3. **Chạy render đúng 1 clip bù**:
     ```bash
     python D:/Taadaa/Tiktok-video/scripts/random_batch_render.py --input-dir "D:/video goc/<folder>" --output-dir "D:/TIKTOK-videonuoinick/<folder>" --file-list "C:/Users/Kibe/AppData/Local/Temp/list_patch.txt" --preset "presets/preset_owner.json" --randomize --slot <slot_0_idx> --machine-id <m_0_idx> --start-seq <N_tiep_theo> --parallel 1
     ```
  4. **Kiểm tra & Dọn dẹp**: Xóa file list tạm. Xác nhận folder đạt 30 clips. Watchdog tự động nhảy trạng thái `80/80 [100.0%]`.

---

## 9. Chuẩn Video Render & Nguồn Toàn Farm Mới: Min 40 – Đích 45 Clip (User Invariant 2026-10-03)
- **Chỉ thị dứt khoát từ User**: *"Ủa????? T đổi chuẩn phải sang 45 clip r mà. Min 40"* -> *"Chuyển lên 45 r sửa hết đi"*.
- **Quy tắc cốt lõi (Hard Invariant)**:
  - **Chuẩn cũ $\ge 30$ clip ĐÃ BỊ LOẠI BỎ HOÀN TOÀN**.
  - **Chuẩn mới toàn farm**: **Tối thiểu Min 40 clip, đích đến 45 clip (Min 40 – Max 45)** cho mỗi folder nguồn và render thành phẩm.
- **Kỷ luật Báo cáo Watchdog (`farm_render_download_watchdog.py`)**:
  - TUYỆT ĐỐI CẤM đánh giá `100%` hay `✅ Hoàn thành` dựa trên mốc cũ $\ge 30$ clip. Mọi folder chỉ có 30–44 clip BẮT BUỘC bị coi là CHƯA ĐỦ CHUẨN (vàng 🟡).
  - Watchdog bắt buộc tính tỷ lệ hoàn thành theo mốc **$\ge 45$ clip** (`ge45 / 80` [pct = ge45/80*100]). Chỉ hiển thị `✅ Tik{slot}: 80/80 folder (≥45 clip) [100.0%]` khi toàn bộ 80 folder đều có đủ $\ge 45$ clip.
- **Kỷ luật Script Render (`run_tik*.ps1`)**:
  - Điều kiện kiểm tra video nguồn: Bắt buộc $\ge 40$ clip (`$sourceMp4.Count -lt 40 -> SKIP`).
  - Lệnh chọn video: `select_videos(..., min_videos=40, max_videos=45)`.
  - Điều kiện skip folder đã render: Bắt buộc `-ge 45` (`$existing.Count -ge 45`). CẤM dùng `-ge 30` vì sẽ skip non các folder mới có 30–44 clip khiến kho không được bù lên 45 clip.
- **Kỷ luật Điều Phối Worker Render trên Admin**:
  - Khi User chơi game / cần CPU: Tree-kill toàn bộ tiến trình render, hạ `--parallel 1`.
  - Khi User yêu cầu cày hết tốc độ (*"Chạy worker 2 nốt cho tao"*): Nâng `--parallel 2` (2 workers FFmpeg song song). Kích hoạt detached Session 0 qua WMI để bất tử trước ngắt kết nối SSH.

---

## 10. Xử Lý Tràn Đĩa Admin D: (0 Bytes Free) & Tự Động Phục Hồi Pipeline Cào/Render (2026-10-06)
- **Triệu chứng & Nguyên nhân**:
  - Ổ D: máy Admin bị chạm ngưỡng 0 bytes free (tràn 100%).
  - Cả Downloader (`yt-dlp`) và Render (`ffmpeg`) đều bị dừng/crash hoặc không thể tạo file mới.
  - Phân tích đĩa Admin: Thư mục render `D:\TIKTOK-videonuoinick-admin` chiếm ~684 GB, Thư mục Game Riot Games `D:\x\Riot Games` chiếm ~86 GB (LoL 36.7 GB, LoL PBE 36.5 GB, TFT 12 GB), Thư mục video gốc `D:\video goc may 2` chiếm ~69 GB.
  - **BẪY CHUYỂN GAME SANG Ổ C**: Ổ C chỉ còn ~50 GB trống, nếu move toàn bộ thư mục Riot Games (85.8 GB) sang C sẽ làm tràn ổ C hệ thống về 0 GB, gây treo/sập Windows.
- **Quy trình dọn dẹp an toàn O(1) giải phóng 30–60 GB**:
  - Đối soát thư mục nguồn `D:\video goc may 2\{src_id}` với output render tương ứng qua workbooks `Tik1..Tik8.xlsx`.
  - Với mọi folder mà thành phẩm render trong `D:\TIKTOK-videonuoinick-admin\{out_id}` đã đạt chuẩn $\ge 45$ clip:
    + **CHỈ XÓA các file video `.mp4` và `.part`** trong thư mục nguồn `D:\video goc may 2\{src_id}`.
    + **BẢO LƯU TUYỆT ĐỐI file `avatar.jpg` và `channel_info.json`**.
    + Thao tác này ngay lập tức thu về 32–60 GB dung lượng trống mà không ảnh hưởng tới vận hành và không đụng vào game.
- **Khắc phục Downloader dừng do cạn Manifest & Bẫy `INFECTED_FOLDERS` cũ**:
  - Script downloader cũ dừng do `source_manifest_admin_vn.jsonl` chỉ có 576 kênh (đã claim 481 kênh) và có mảng tĩnh `INFECTED_FOLDERS`.
  - **Giải pháp chuẩn hóa**:
    1. Bỏ mảng tĩnh `INFECTED_FOLDERS`.
    2. Tự động tính toán động danh sách folder thiếu: `source < 40` VÀ `render < 45`.
    3. Nạp nguồn bổ sung từ `D:\OneDrive\SharedData\tiktok-video\sources.master_1288.json` (có sẵn $\ge 1.000$ kênh YouTube Shorts tiếng Việt chưa claim).
    4. Cấu hình `yt-dlp` dùng cookie `D:\CodexRuntime\tiktok-video\youtube-cookies.txt`, `--merge-output-format mp4`, tự động đổi tên `1.mp4..45.mp4` và trích frame tạo `avatar.jpg`.
    5. Khởi chạy ngầm Session 0 qua WMI bằng launcher `run_admin_downloader.bat` để chạy song song bền bỉ cùng `run_admin_render_chain.bat`.
  - **Bẫy Cookie Truncate 0-Byte Khi Đĩa Tràn & Khôi Phục O(1)**:
    Khi đĩa D: chạm 0 byte, `youtube-cookies.txt` có thể bị truncate về 0 byte. Khi đó `yt-dlp` lỗi `does not look like a Netscape format cookies file`, làm hỏng toàn bộ đợt tải (0 video/kênh) và downloader thoát sớm sau vài phút. Kiểm tra `Get-Item youtube-cookies.txt | Select Length`, nếu = 0 thì SCP copy lại file cookie chuẩn từ Kibe sang Admin.
  - **Khóa Chống Trộn Kênh Trong Downloader (Anti-Mixing Invariant)**:
    Trong `run_admin_clean_vn_downloader.py`, nếu một kênh có `< 35` video, trước khi chuyển sang thử kênh tiếp theo bắt buộc phải dọn sạch các file `.mp4`, `.part`, `.jpg` dở dang trong folder để bảo toàn invariant 1 folder = 1 kênh duy nhất.
  - **Đồng Bộ Watchdog Nhận Diện Downloader**:
    Hàm `is_download_running()` trong `farm_render_download_watchdog.py` trên cả Kibe và Admin bắt buộc phải kiểm tra thêm các chuỗi `clean_vn`, `run_admin_clean_vn`, `run_admin_downloader` để hiển thị chính xác trạng thái `🟢 Đang chạy`.
  - **Khóa Cứng Invariant Cào ĐÚNG NICHE Theo Từng Folder (Anti-Niche-Mismatch Invariant)**:
    - **Bẫy lệch niche khi tải bù**: Khi viết script tải bù (như `run_admin_clean_vn_downloader.py`), nếu chỉ duyệt `available_channels` từ master manifest chung chung mà KHÔNG tra cứu `niche` của folder, các folder chuyên biệt (ví dụ 256 tâm lý, 384 câu chuyện, 504 thiền, 505 kinh doanh...) sẽ bị nhồi các kênh ngẫu nhiên (ẩm thực, bóng đá, tin tức...) gây sai lệch hoàn toàn chủ đề tài khoản nuôi.
    - **Quy tắc bắt buộc**:
      1. Tra cứu `niche` O(1) từ SQLite `state.db` (`D:\CodexRuntime\tiktok-video-machine2\state.db` trên Admin): `SELECT niche FROM folders WHERE folder_num = ?`.
      2. Lọc kênh chính xác: Chỉ lấy các kênh trong `sources.master_1288.json` có `folder_niche in [n.lower() for n in c.get('niches', [])]`.
      3. Xử lý khi phát hiện cào lệch: Thu hồi claims tương ứng trong `admin_channel_claims.json`, dọn sạch toàn bộ file media lệch trong folder nguồn, reset output render tương ứng (nếu đã render nhầm nguồn lệch) và chạy lại đúng niche.

---

## 11. Kỷ Luật Khởi Chạy Script Python Qua SSH Trên Windows (CP1252 Crash & Reconfigure UTF-8)
- **Triệu chứng & Bẫy CP1252**:
  - Khi viết script Python tiện ích rồi bắn sang Windows Admin qua SCP/SSH để chạy nền, môi trường shell Windows mặc định encoding là `cp1252`.
  - Bất kỳ chuỗi tiếng Việt Unicode có dấu nào trong code (kể cả trong `print()` hoặc log) đều văng lỗi ngay lập tức:
    ```text
    UnicodeEncodeError: 'charmap' codec can't encode character '\u1eae' in position 5: character maps to <undefined>
    ```
  - Script crash ngay ở dòng 1 và trả về `exit code 1` trong im lặng nếu không đọc log.
- **Quy tắc Bắt buộc (Mandatory Invariant)**:
  - MỌI script Python thực thi trên Windows từ xa bắt buộc phải thêm cấu hình reconfigure UTF-8 ngay sau `import sys`:
    ```python
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    ```
  - Đồng thời, khi gọi qua SSH/bash, thêm cờ `PYTHONUTF8=1` và `PYTHONIOENCODING=utf-8` trong environment.

---

## 12. Kỷ Luật Đồng Bộ Sổ Cái Excel Với FileSystem Thật (Excel Desync Remediation)
- **Hiện tượng**:
  - Trên farm Kibe (và Admin), các đợt render trước đó đã xử lý xong hàng trăm folder trong `D:\TIKTOK-videonuoinick` (ví dụ đạt 591/640 folder $\ge 45$ clip), nhưng các file Excel `Tik1.xlsx..Tik8.xlsx` vẫn ghi `Render Status: None` và `Render MP4: 0` (hoặc rỗng).
  - Operator hoặc Watchdog nhìn vào Excel tưởng hệ thống chưa render gì, dẫn đến hoang mang hoặc kích hoạt render trùng lặp gây lãng phí CPU.
- **Quy trình Quét & Đồng bộ O(1)**:
  - Viết script duyệt qua toàn bộ 8 file `Tik1..Tik8.xlsx`, đọc cột `output_folder_id` (cột 4).
  - Đếm số file `.mp4` thực tế trong `D:\TIKTOK-videonuoinick\<out_id>`.
  - Cập nhật trực tiếp:
    - Cột `Render Status`: `'OK'` (nếu $\ge 40$ clip) hoặc `'PARTIAL'` (nếu $> 0$ và $< 40$).
    - Cột `Render MP4`: Số file MP4 thực tế đếm được.
    - Cột `Render Date`: Timestamp hiện tại.
  - Lưu lại workbook. Sau khi chạy, tỷ lệ hoàn tất trên Excel sẽ lập tức khớp 100% với thực tế ổ đĩa.


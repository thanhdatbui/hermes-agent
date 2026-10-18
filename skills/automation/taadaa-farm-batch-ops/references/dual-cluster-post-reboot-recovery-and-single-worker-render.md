# Quy Trình Phục Hồi Sau Reboot & Kỷ Luật Render Đơn Luồng (Dual-Cluster Kibe - Admin)

## 1. BỐI CẢNH & NGUYÊN TẮC VẬN HÀNH DUAL-CLUSTER
- Hệ thống Taadaa Phone Farm video vận hành trên 2 cụm máy độc lập:
  - **Host Kibe (Local)**: Máy điều phối chính, kho video gốc tại `D:\video goc`, thành phẩm tại `D:\TIKTOK-videonuoinick`.
  - **Host Admin (Remote qua SSH `admin-farm`)**: Máy phụ, kho video gốc tại `D:\video goc may 2`, thành phẩm tại `D:\TIKTOK-videonuoinick-admin`.
- **Cơ chế chống trùng nguồn**: Toàn bộ worker cào trên cả 2 máy bắt buộc sử dụng `global_ledger.py` đồng bộ qua thư mục OneDrive dùng chung `D:\OneDrive\SharedData\tiktok-video\global-ledger` với tham số `--ledger-machine-id {Kibe|Admin}`.

---

## 2. CHECKLIST PHỤC HỒI SAU KHI REBOOT (POST-REBOOT RECOVERY)

Khi User hoặc hệ thống reboot 1 hoặc cả 2 máy, toàn bộ các tiến trình nền download/render sẽ bị ngắt. Coordinator cần thực hiện theo các bước sau:

### Bước 1: Kiểm tra kết nối & tiến trình tự khởi động
- **Trên Kibe**:
  - Kiểm tra các process tự chạy: `hermes gateway`, `run_tiktok.py` (feed session), `social_reg_v1.py` (reg).
  - Kiểm tra tình trạng kho gốc: `D:\video goc` (thường đã hoàn tất 640/640 folder).
- **Trên Admin**:
  - Kiểm tra kết nối SSH: `ssh -o ConnectTimeout=5 admin-farm "powershell -Command Write-Output 'OK'"`
  - Kiểm tra process nền qua: `ssh admin-farm "powershell -Command Get-Process -Name python,ffmpeg -ErrorAction SilentlyContinue"`

### Bước 2: Kích hoạt lại tiến trình Render trên Kibe
- Lọc danh sách các account/folder trong `Tik1.xlsx` .. `Tik8.xlsx` có số video thành phẩm `< 45`.
- Chạy render bù tuần tự với cấu hình khóa cứng:
  ```bash
  python -u C:/Users/Kibe/run_kibe_render_all37.py > "D:\CodexRuntime\tiktok-video\batch-runs\kibe_under45_fix\render_all37_postreboot.log" 2>&1
  ```
  - Cờ bắt buộc: `--parallel 1` (đúng 1 worker ffmpeg), `--resume-verify-existing` (chỉ render clip còn thiếu).

### Bước 3: Kích hoạt lại 2 mũi Cào + Render trên Admin
- **Mũi 1: Cào video (10 Worker)**:
  - BẮT BUỘC dùng venv có OpenCV (`cv2`): `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe`
  - Lệnh chạy:
    ```bash
    D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe -u D:\Taadaa\Tiktok-video\scripts\download_by_niche.py \
      --total-folders 640 \
      --sources D:\OneDrive\SharedData\tiktok-video\sources.qualified30.json \
      --niche-pool D:\Taadaa\Tiktok-video\data\niches_pool.txt \
      --exclusion-list D:\Taadaa\Tiktok-video\data\exclusion_list.txt \
      --verified-channels D:\Taadaa\Tiktok-video\data\verified_vn_channels.jsonl \
      --state-db D:\CodexRuntime\tiktok-video-machine2\state.db \
      --runtime D:\CodexRuntime\tiktok-video-machine2 \
      --output-root "D:\video goc may 2" \
      --niche-mode strict \
      --min-videos 45 --target-videos 45 --max-videos 65 \
      --max-folders-per-channel 2 \
      --parallel 10 \
      --continue-on-insufficient \
      --all-languages \
      --proxy-pool D:\Taadaa\Tiktok-video\proxy_pool_69.txt \
      --global-ledger-dir D:\OneDrive\SharedData\tiktok-video\global-ledger \
      --ledger-machine-id Admin
    ```
  - **Lưu ý Proxy**: BẮT BUỘC dùng pool **69 proxy MikroTik** (`proxy_pool_69.txt` hoặc `proxy_pool_67.txt`). CẤM dùng pool direct (`proxy_pool_67_direct.txt`) vì dễ bị lỗi mạng âm thầm không báo cáo.
- **Mũi 2: Continuous Render Worker (1 Worker - BẮT BUỘC MAPPING QUA 8 TIK)**:
  - Chạy `C:\Users\Admin\run_admin_render_worker.py` trong vòng lặp liên tục.
  - **CẤM TUYỆT ĐỐI mapping 1-to-1 (`out_d = rr_root / d.name`)**. Script render BẮT BUỘC phải đọc qua `D:\OneDrive\TaadaaData\admin\Tik1.xlsx` .. `Tik8.xlsx`, lấy đúng cặp **Folder Video (Cột D `out_id`) $\leftarrow$ Folder Nguồn Gốc (Cột E `src_id`)**.
  - Render với `--parallel 1`, `--resume-verify-existing`. Lưu ý chuẩn hóa tham số: `--slot` là `(slot - 1) % 8` (0..7) và `--machine-id` là `(m_id - 201) % 80` (0..79).

---

## 3. BẪY KỸ THUẬT & CÁCH XỬ LÝ (PITFALLS)

### Bẫy 1: Orphaned Ffmpeg khi Subprocess Timeout
- **Hiện tượng**: Một số video gốc tải về bị dính clip dài bất thường (> 1 tiếng, e.g. 4000s). Khi chạy `subprocess.run(cmd, timeout=3600)`, Python ném ngoại lệ `TimeoutExpired` và nhảy sang render folder tiếp theo, nhưng tiến trình con `ffmpeg.exe` KHÔNG tự thoát mà tiếp tục chạy ngầm.
- **Hậu quả**: Xuất hiện 2 tiến trình ffmpeg chạy đồng thời, tranh chấp 100% CPU và ăn hơn 3.5GB RAM, làm đơ máy và vi phạm quy định `--parallel 1`.
- **Cách xử lý**:
  - Khi bắt ngoại lệ `subprocess.TimeoutExpired`, bắt buộc phải kill process group hoặc kiểm tra `Get-Process -Name ffmpeg` để kill các PID ffmpeg mồ côi.
  - Kiểm tra thời lượng file nguồn trước khi render, loại bỏ hoặc cắt ngắn các clip > 180s.

### Bẫy 2: Lỗi Quota / SSH Shell Quote Mất Format trên Windows
- Khi gửi lệnh PowerShell phức tạp chứa `$_.FullName` hoặc inner quotes qua SSH từ Git Bash sang Windows Admin, PowerShell sẽ hiểu nhầm biến nội bộ.
- **Giải pháp**: Tạo file `.py` trên Kibe rồi dùng `scp` đẩy sang `C:/Users/Admin/` và gọi qua SSH `python C:/Users/Admin/<script>.py`.

### Bẫy 3: Đánh Giá Sức Khỏe Tiến Trình Qua RAM (WorkingSet)
- `ffmpeg.exe` hoạt động bình thường ăn từ **1.5 GB đến 2.0 GB RAM**.
- `download_by_niche.py` (10 worker) ăn từ **200 MB đến 350 MB RAM**.
- Nếu thấy Python chỉ ăn 3-10 MB RAM thì có thể tiến trình đã crash ở đoạn import hoặc kết thúc sớm (cần kiểm tra log ngay).

### Bẫy 4: Lỗi Sai Mapping 1-to-1 trên Admin vs Chuẩn Mapping 8 Tik Workbook
- **Hiện tượng**: Viết code tiện tay gán `out_d = rr_root / d.name` (lấy folder `N` từ `D:\video goc may 2` xuất thẳng sang `D:\TIKTOK-videonuoinick-admin\N`).
- **Hậu quả nghiêm trọng**:
  - Mapping chuẩn của Farm là Folder Video (1..640) mapping chéo với video gốc (1..640) qua file `Tik1.xlsx` .. `Tik8.xlsx`.
  - Ví dụ: Máy 203 Row 6 đăng từ Folder Video = 22, nhưng nguồn là video gốc = 403. Nếu script lấy video gốc 403 nhét vào folder 403 (thay vì 22), thì máy 203 bị rỗng đạn, còn folder 22 lại bị nhét video gốc 22 (thuộc máy khác).
  - Điều này làm cho các thư mục thành phẩm của các slot Tik 2..8 luôn bị bỏ trống hoặc sai niche.
- **Quy tắc bắt buộc**: Script render BẮT BUỘC phải đọc trực tiếp 8 workbook (`D:\OneDrive\TaadaaData\admin\Tik1..8.xlsx`), lấy đúng cặp `out_id` (Cột D) $\leftarrow$ `src_id` (Cột E).

### Bẫy 5: Lỗi Argparse Bounds (`returncode 2`) Trong `random_batch_render.py`
- `--slot`: Chỉ chấp nhận các giá trị từ `0..7` (0-indexed). CẤM truyền số slot 1..8 trực tiếp từ file Excel. Bắt buộc chuyển đổi: `(slot - 1) % 8`.
- `--machine-id`: Chỉ chấp nhận các giá trị từ `0..79`. Đối với dàn máy Admin (máy 201..280), cấm truyền trực tiếp `201..280` (sẽ dính `invalid choice` và thoát returncode 2 ngay lập tức). Bắt buộc chuẩn hóa: `(m_id - 201) % 80`.

### Bẫy 6: Cấm Cào Direct Âm Thầm Khi Proxy Lỗi — Bắt Buộc Dùng Pool 69 MikroTik & Kill Restart Ngay
- **Hiện tượng**: Pool proxy direct (`proxy_pool_67_direct.txt` dải Mobi ngoài) thường xuyên chập chờn, dính rate limit hoặc chết âm thầm. Tiến trình cào fail ngầm, cào không ra video nhưng không văng lỗi rõ ràng hoặc không báo về chat.
- **Kỷ luật xử lý**:
  - Toàn bộ script cào trên cả Kibe và Admin (`download_by_niche.py`, `auto_rescan_loop.py`, `run_admin_foreground_loop.py`, service) **BẮT BUỘC dùng pool 69 proxy MikroTik** (`D:\Taadaa\Tiktok-video\proxy_pool_69.txt` hoặc `proxy_pool_67.txt` trỏ IP LAN MikroTik `192.168.110.2:10001..10035`). Pool này sống 100%, phản hồi < 0.2s.
  - Khi phát hiện tiến trình cào đang ăn pool direct cũ/lỗi, **CẤM TUYỆT ĐỐI đứng chờ tiến trình chạy xong một cách thụ động**. BẮT BUỘC kill tiến trình cũ và restart ngay lập tức với cờ `--proxy-pool D:\Taadaa\Tiktok-video\proxy_pool_69.txt`.

### Bẫy 7: Cơ Chế Smart Idle & Chống Trùng Tiến Trình Giữa Startup VBS và Watchdog 15p
- **Smart Idle**:
  - Trước mỗi vòng quét, service cào/render phải kiểm tra toàn bộ 640 folder (`D:\video goc` hoặc `D:\TIKTOK-videonuoinick`).
  - Nếu tất cả 640/640 folder đều đã đạt $\ge 45$ clip `.mp4`, tiến trình tự động dừng hoàn toàn (`sys.exit(0)`), trả lại 100% CPU/RAM/ổ đĩa.
- **Khóa Lock msvcrt & Watchdog Im Lặng**:
  - Sử dụng file lock độc quyền `msvcrt.locking` tại `AppData/Local/hermes/locks/`.
  - Watchdog chạy mỗi 15 phút (cả Cronjob và Startup VBS) chỉ spawn worker mới khi kho THIẾU CLIP (< 640 folder đạt 45 clip) VÀ CHƯA CÓ INSTANCE NÀO CHẠY.
  - Khi đã đủ hoặc instance đang chạy, watchdog giữ `stdout` rỗng tuyệt đối (0% CPU, không log rác, không spam báo cáo).
- **Kênh Báo Cáo Định Kỳ**:
  - Cron `farm-render-download-watchdog` chạy mỗi 6h (`0 */6 * * *`) đẩy trực tiếp về nhóm Telegram **Tiktok video** (`telegram:-5435853713`), chế độ `no_agent=true`.

### Bẫy 8: Busy-Loop Khi Nguồn Cạn Video Mới (`src_cnt <= out_cnt`) & Kỷ Luật Bổ Sung Nguồn
- **Hiện tượng**: Worker hoặc watchdog kiểm tra điều kiện nhận việc chỉ dùng `out_cnt < 45` và `src_cnt >= 35`, bỏ quên điều kiện `src_cnt > out_cnt`. Khi folder gốc chỉ có đúng số video đã được render (ví dụ: `src_cnt = 40`, `out_cnt = 40`), worker liên tục spawn `random_batch_render.py` với cờ `--resume-verify-existing`. Lệnh render thấy 40/40 clip đã tồn tại và hợp lệ nên thoát sau 1s mà không encode clip nào. Worker lặp lại quét mỗi 5s, tạo ra busy-loop ngầm hàng nghìn lần, ghi log phình to hàng chục ngàn dòng và watchdog báo render "đang dừng" vì ffmpeg không hoạt động.
- **Cách xử lý & Điều kiện chuẩn**:
  - Điều kiện nhận việc của Worker và Watchdog BẮT BUỘC phải kiểm tra:
    ```python
    if out_cnt < 45:
        if src_cnt >= 35 and src_cnt > out_cnt:
            # Nhận việc render
    ```
  - Khi một folder thành phẩm bị kẹt chưa đủ 45 clip vì nguồn cạn (ví dụ Tik7 M31 Out 247 kẹt 40/45 do Src 247 chỉ có 40 clip):
    1. Kiểm tra chính xác Niche của folder (ví dụ Âm nhạc, Acoustic, Cười, v.v.).
    2. Dùng yt-dlp cào bổ sung thêm các clip Shorts mới chất lượng cao đúng niche vào thư mục nguồn `D:\video goc\<src_id>` để nâng tổng clip gốc lên $\ge 45$.
    3. Chạy render với `--resume-verify-existing` để render nốt các clip còn thiếu (`41.mp4`..`45.mp4`) lên đích.

### Bẫy 9: SSH Background Process Exit Code 255 & Detached Process Isolation
- **Hiện tượng**: Khi Coordinator chạy lệnh nền từ xa qua SSH (e.g. `ssh admin-farm "python -u ... > log 2>&1"`):
  - Bất kỳ thao tác kill tiến trình cũ (để giải phóng lock ổ đĩa trước khi realign thư mục), rớt mạng LAN, hoặc reset máy Admin sẽ khiến tiến trình SSH trả về cảnh báo `exited (exit code 255)`.
- **Kỷ luật xử lý**:
  - Coordinator KHÔNG được hoảng loạn hoặc kết luận toàn bộ tiến trình render/cào đã chết. BẮT BUỘC kiểm tra liveness của `ffmpeg.exe` hoặc `python.exe` qua lệnh không vướng SSH pipe hoặc qua log đuôi.
  - Để tiến trình render Admin sống sót hoàn toàn độc lập với SSH session: ưu tiên đẩy script launcher detached (`Start-Process python -ArgumentList ... -WindowStyle Hidden` qua PowerShell hoặc dùng `subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS` trong script launcher Python).

### Bẫy 10: Chống Im Lặng Khi Tác Vụ Nền Kéo Dài (Anti-Silence & Proactive Telemetry)
- **Tín hiệu người dùng**: Người dùng bức xúc ("Sao r chả thấy cạp nhật v") khi Coordinator giữ im lặng quá lâu trong lúc các tiến trình render hàng chục folder đang chạy ngầm (mỗi folder mất 15-30 phút).
- **Kỷ luật điều phối**:
  - Khi quản lý batch render/cào đường dài, mỗi khi nhận sự kiện hoàn thành của một subprocess con hoặc sau mỗi checkpoint kiểm tra, BẮT BUỘC chủ động cập nhật tóm tắt hiện trường cho User:
    + Số lượng folder đã hoàn tất / tổng số folder (kèm phần trăm rõ ràng, e.g. `611/640 (95.5%)`).
    + Tên và folder cụ thể đang render trực tiếp (e.g. `Tik7 M41 Out 327 <- Src 521`).
    + PID phần cứng và dung lượng RAM của các tiến trình chủ chốt (`ffmpeg.exe`, `python.exe`).
  - Tuyệt đối không chờ đến khi toàn bộ batch 30-40 folder chạy xong mới báo cáo.

### Bẫy 11: Chống Spawn Trùng Tiến Trình Khi User Lệnh "Fix Đi" Cho Folder Render Chưa Đủ
- **Hiện tượng**: Báo cáo watchdog (cronjob 6h) báo farm "Đang dừng" hoặc một folder chưa đủ 45 clip (ví dụ Tik 1 thiếu Folder 441 [79/80 folder]). Khi User ra lệnh ngắn gọn *"Fix đi"*, phản xạ vội vàng của Coordinator là gõ ngay lệnh render lại folder đó.
- **Nguy cơ nghiêm trọng**:
  - Snapshot trong cronjob phản ánh trạng thái quá khứ (ví dụ lúc 18:00). Giữa 18:00 và thời điểm User chat, một tiến trình render ngầm có thể đã được trigger hoặc đang chạy nền qua gateway/service (`random_batch_render.py`).
  - Nếu Coordinator không kiểm tra tiến trình mà lập tức gọi lệnh render mới, 2 tiến trình `ffmpeg.exe` sẽ chạy song song ghi cùng vào 1 thư mục đích, gây xung đột file lock, nghẽn 100% CPU/GPU, làm corrupt video và vi phạm quy định `--parallel 1`.
- **Kỷ luật xử lý 2 bước (Pre-flight Process & Growth Probe)**:
  1. **Process Liveness Probe**: Quét danh sách process (`psutil.process_iter`) kiểm tra xem có `ffmpeg.exe` hoặc `random_batch_render.py` nào đang chứa đối số trỏ về folder đó không (ví dụ `--output-dir .../441`).
  2. **File Growth Probe**: Đếm số clip hiện tại trong folder đích (`len(list(folder.glob("*.mp4")))`) và kiểm tra `mtime` của các clip mới nhất. Nếu clip đang tăng dần (ví dụ 24 -> 27 -> 31 -> 34 clip) và có file vừa sinh trong vài phút gần nhất:
     - **CẤM TUYỆT ĐỐI** spawn thêm bất kỳ lệnh render nào.
     - Xác định rõ tiến trình cha (PID), số clip đã có / tổng clip gốc, và báo cáo tiến độ trực tiếp cho User kèm thời gian dự kiến hoàn tất.
  3. **Chỉ spawn khi probe xác nhận hoàn toàn chết (Dead confirmed)**: Khi không có process nào chạy VÀ số lượng file không đổi sau probe mtime, mới được phép kích hoạt 1 worker đơn luồng duy nhất (`--parallel 1`) với cờ `--resume-verify-existing` để render bù clip còn thiếu.

### Bẫy 12: Tử Huyệt Thư Mục Startup Của Windows Sau Reboot Tự Động & Cháy Watchdog
- **Hiện tượng**: Trên máy Admin (`admin-farm`), sau ca reboot định kỳ (05:20 hoặc 17:20), cả tiến trình cào (`download_by_niche.py`) và render (`run_admin_render_worker.py`) đều dừng hoàn toàn, không tự động chạy lại dù đã có file `.vbs` trong `shell:startup` (`C:\Users\Admin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\`).
- **Nguyên nhân cốt lõi**:
  1. **Startup Folder chỉ chạy khi có User đăng nhập GUI (Interactive Logon)**: Khi máy reboot tự động lúc rạng sáng, Windows dừng ở Lock Screen. Không có interactive logon thì Startup folder KHÔNG BAO GIỜ được nạp.
  2. **Watchdog thiết kế chạy 1 lượt (Single-shot exit 0)**: Script `watchdog_admin_downloader.py` và `watchdog_admin_render.py` được viết theo kiểu kiểm tra 1 lần rồi `return 0`, không phải vòng lặp daemon. Nếu không có bộ lập lịch định kỳ (cronjob/Task Scheduler) gọi lặp lại thì sau khi worker bị kill bởi reboot (mã thoát `1073807364`) hoặc timeout (2400s), hệ thống sẽ nằm im vĩnh viễn.
  3. **Proxy Loopback 502 Bad Gateway trên mạng LAN**: File cấu hình proxy trên Admin (`proxy_pool_69.txt`) nếu trỏ vào domain ngoài `mirotik1.taadaa.click` sẽ bị router từ chối (502) khi gọi từ trong LAN `192.168.110.119`. BẮT BUỘC dùng IP LAN nội bộ `192.168.110.2:10001..10035`.
- **Kỷ luật khắc phục dứt điểm**:
  - Không bao giờ dựa duy nhất vào thư mục Startup cho các tác vụ nền quan trọng của Farm.
  - Phải đăng ký vào **Windows Task Scheduler (Trigger: At Startup / At boot)** chạy ngầm độc lập với user logon, HOẶC duy trì một cron watchdog định kỳ (e.g. `*/15 * * * *`, `deliver: local`) để tự động kiểm tra và hồi sinh worker khi phát hiện chết tiến trình.




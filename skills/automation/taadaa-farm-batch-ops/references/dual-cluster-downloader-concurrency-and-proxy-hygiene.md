# Dual-Cluster Downloader Concurrency, Proxy Hygiene & Global Ledger Dedup

## 1. Concurrency Parity: Kibe vs Admin Downloader
- **Kibe Downloader**: `run_download_kibe.py` chạy với `--parallel 20` (20 workers song song).
- **Admin Downloader**: Service nền chạy tại `C:\Users\Admin\run_admin_downloader_service.py` trên máy Admin. Mặc định có thể được cấu hình `--parallel 10` trừ khi được cập nhật lên `--parallel 20`.
- **Kiểm tra tiến trình thực tế**:
  - Không dựa vào số lượng `python.exe` từ `tasklist` vì trên Windows, mỗi venv python stub (`venv\Scripts\python.exe`) sẽ spawn 1 tiến trình interpreter chính (`AppData\Local\Programs\Python\Python311\python.exe`), tạo ra 2 PIDs cho cùng 1 tác vụ logic.
  - Sử dụng lệnh psutil chính xác qua SSH để kiểm tra command line thực tế:
    ```bash
    ssh admin-farm "python -c \"import psutil; [print(p.pid, ' '.join(p.cmdline())) for p in psutil.process_iter(['pid', 'cmdline']) if p.info['cmdline'] and 'download_by_niche' in ' '.join(p.info['cmdline'])]\""
    ```

## 2. Proxy Hygiene & Pool Drift giữa 2 máy
- File pool proxy tiêu chuẩn: `D:\Taadaa\Tiktok-video\proxy_pool_69.txt` (35 cổng MikroTik + 32 cổng Mobi 4G + 2 cổng DuckDNS).
- **Nguy cơ Drift**: Máy Admin và Kibe có thể bị lệch file proxy cục bộ (ví dụ: dòng 69 trên Admin bị ghi đè IP tĩnh cũ thay vì domain DuckDNS động). Khi IP cũ đổi hoặc hết hạn, yt-dlp sẽ liên tục gặp `ConnectTimeoutError`.
- **Rà soát**:
  - So sánh hash file giữa 2 máy:
    ```powershell
    (Get-FileHash D:\Taadaa\Tiktok-video\proxy_pool_69.txt).Hash
    ```
  - Cơ chế xoay: `next_proxy()` xoay round-robin từng video (`_PROXY_IDX % len(pool)`). Khi gặp lỗi kết nối proxy, `yt-dlp` thử lại candidate ở vòng lặp tiếp theo sẽ lấy proxy kế tiếp trong pool.

## 3. Global Ledger Deduplication & Channel Exclusivity Policy
- **Shared Ledger Path**: `D:\OneDrive\SharedData\tiktok-video\global-ledger` (chứa `Admin.jsonl` và `Kibe.jsonl`).
- **Cơ chế Claim**:
  - Trước khi tải hoặc nạp kênh vào folder, worker gọi `read_source_keys()` nạp toàn bộ claim của cả 2 máy.
  - Nếu kênh đã thuộc máy kia hoặc folder khác -> `SOURCE_SKIP_GLOBAL reason=source_claimed_elsewhere`.
  - Auto-discovery cũng nạp `existing_keys` từ shared ledger để không crawl trùng kênh đã tồn tại ở bất kỳ máy nào.
- **Quy tắc `--max-folders-per-channel` (Khóa độc quyền kênh)**:
  - Giá trị `2`: Cho phép 1 kênh lớn cấp nguồn cho tối đa 2 folder khác nhau (clip khác nhau, không trùng `video_id`). Từng dùng để chống thiếu nguồn ở ngách hẹp tiếng Việt.
  - **Quy chuẩn chốt (`1`)**: Vào giai đoạn nạp nốt các folder còn lại hoặc khi cần kỷ luật độc quyền tuyệt đối (1 nick = 1 kênh riêng, cấm chung chủ kênh dù khác clip), BẮT BUỘC cấu hình `--max-folders-per-channel 1`.

## 4. Quy trình Restart Downloader Service An toàn trên Admin
- **Cách ly với Render**: Trên Admin luôn có render worker (`run_admin_render_worker.py` / `random_batch_render.py` / `ffmpeg`) chạy ngầm. CẤM `taskkill /F /IM python.exe` diện rộng.
- **Quy trình restart downloader**:
  1. Dùng `psutil` chỉ nhắm mục tiêu các tiến trình chứa `run_admin_downloader_service` và `download_by_niche`.
  2. Đảm bảo xóa stale lock nếu bị kẹt: `C:\Users\Admin\AppData\Local\hermes\locks\admin_downloader.lock`.
  3. Khởi động lại service bằng PowerShell detached:
     ```powershell
     Start-Process -FilePath "D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe" -ArgumentList "C:\Users\Admin\run_admin_downloader_service.py" -WindowStyle Hidden
     ```
  4. Hậu kiểm bằng `psutil` qua SSH xác nhận tiến trình con `download_by_niche.py` đã lên với đúng tham số `--parallel 20` và `--max-folders-per-channel 1`.

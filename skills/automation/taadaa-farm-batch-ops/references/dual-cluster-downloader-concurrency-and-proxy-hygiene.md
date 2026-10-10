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

## 3. Global Ledger Deduplication (Chống trùng kênh)
- **Shared Ledger Path**: `D:\OneDrive\SharedData\tiktok-video\global-ledger` (chứa `Admin.jsonl` và `Kibe.jsonl`).
- **Cơ chế Claim**:
  - Trước khi tải hoặc nạp kênh vào folder, worker gọi `read_source_keys()` nạp toàn bộ claim của cả 2 máy.
  - Nếu kênh đã thuộc máy kia hoặc folder khác -> `SOURCE_SKIP_GLOBAL reason=source_claimed_elsewhere`.
  - Auto-discovery cũng nạp `existing_keys` từ shared ledger để không crawl trùng kênh đã tồn tại ở bất kỳ máy nào.

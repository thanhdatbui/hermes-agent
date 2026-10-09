# Multi-Cluster Reg Bù Operations (Kibe & Admin)

## Architecture & Integration
Khi kích hoạt tính năng reg bù tự động qua `tiktok_runner.py` và `ensure_row_accounts.py`:

1. **tiktok_runner.py**:
   - `_preflight_ensure_accounts(row, window_key, cluster=None)` phải áp dụng đồng bộ cho **cả Kibe và Admin**. Tuyệt đối không hardcode chặn `if cluster_name == "kibe"`.
   - Marker file chống spam 15 phút phải scope theo cluster: `.preflight_{cluster_name}_{window_key}` và đặt trong thư mục state của cluster đó (tránh việc cụm Kibe chạy trước tạo marker chặn luôn cụm Admin).
   - Truyền `TAADAA_HOST_CONFIG` và `ADB_SERVER_SOCKET` từ cluster config vào `child_env` khi gọi subprocess `ensure_row_accounts.py`.

2. **ensure_row_accounts.py**:
   - Khi chạy cho host `admin` từ host Kibe (cross-host runner), hàm `run_tiktok_reg_for_machines` phải đảm bảo biến môi trường `ADB_SERVER_SOCKET` được trỏ tới ADB server của host Admin (mặc định: `tcp:192.168.110.119:5037`).

3. **3-Way Sync Policy**:
   Mọi sửa đổi đối với `tiktok_runner.py` phải được sao chép đồng bộ trên cả 3 đường dẫn:
   - `C:/Users/Kibe/AppData/Local/hermes/scripts/tiktok_runner.py`
   - `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/tiktok_runner.py`
   - `D:/Taadaa/Hermes/deploy/hermes-home/scripts/tiktok_runner.py`

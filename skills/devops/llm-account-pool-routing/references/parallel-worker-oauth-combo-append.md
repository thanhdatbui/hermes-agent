# Parallel Worker OAuth & Combo Append Pattern

## Bối cảnh & Nguyên tắc
Khi nạp lẻ từng tài khoản (worker độc lập, ví dụ Worker 1 chạy máy M52), cần đảm bảo:
1. Không chạy toàn bộ batch lớn gây nghẽn ADB / GPM profile.
2. Tách file thực thi độc lập (ví dụ `scripts/run_m52_parallel.py`) sử dụng hàm cốt lõi `process_account(acc)`.
3. Tự động hook `append_connections` vào combo mục tiêu (ví dụ `ag-gemini-pool-3` tại `http://127.0.0.1:20129`) ngay khi kết quả đạt `SUCCESS` hoặc `ALREADY_SUCCESS`.

## Cấu trúc Script Worker Độc Lập
```python
import sys, os, time, logging
sys.path.insert(0, r"D:\Taadaa\GPM auto\scripts")
from run_oauth_s7_pipeline import process_account
from append_to_combo_pool3 import append_connections

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("worker")

acc = {
    "mid": 52,
    "email": "taquynh06011998@gmail.com",
    "password": "...",
    "totp_secret": "...",
    "port": 5116,
    "singbox_port": 20052,
    "serial": "ce0418243a6250430c",
    "profile": "M52 - 5116 - taquynh06011998@gmail.com"
}

res = process_account(acc)
if res.get("status") in ["SUCCESS", "ALREADY_SUCCESS"] and res.get("conn_id"):
    cid = res["conn_id"]
    append_connections([{"cid": cid, "email": acc["email"], "port": acc["port"]}])
```

## Kiểm Tra & Xác Minh (Verification)
- Đọc `oauth_pipeline_status.json`: kiểm tra email đã được ghi nhận trong `omniroute_success`.
- Truy vấn API live OmniRoute: `GET http://127.0.0.1:20129/api/combos` -> đối chiếu `models` của combo có chứa target với `connectionId == res['conn_id']`.

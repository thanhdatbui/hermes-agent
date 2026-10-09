# Standalone Parallel Account OAuth Pipeline & Pool Append Pattern

Khi nạp OAuth độc lập hoặc chạy worker song song cho từng máy/tài khoản (ví dụ M53, M54, M55...) qua pipeline Samsung S7 + GPM + Singbox và append vào combo OmniRoute:

## 1. Cấu trúc runner script song song / độc lập
Tạo runner script ngắn gọn import trực tiếp pipeline core:
```python
import sys, os, time, logging
sys.path.insert(0, r"D:\Taadaa\GPM auto\scripts")
from run_oauth_s7_pipeline import process_account
from append_to_combo_pool3 import append_connections

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("worker_name")

acc = {
    "mid": <machine_id>,
    "email": "<email>",
    "password": "<password>",
    "totp_secret": "<totp>",
    "port": <farm_port>,               # ví dụ 5117
    "singbox_port": <singbox_port>,    # ví dụ 20053 (20000 + mid)
    "serial": "<adb_serial>",
    "profile": "<gpm_profile_name>"
}

res = process_account(acc)
logger.info(f"Result: {res}")
if res.get("status") in ["SUCCESS", "ALREADY_SUCCESS"] and res.get("conn_id"):
    cid = res["conn_id"]
    append_connections([{"cid": cid, "email": acc["email"], "port": acc["port"]}])
    logger.info(f"✅ Appended {cid} to combo pool!")
```

## 2. Quy tắc đối chiếu & Verification
- `append_connections` cập nhật combo trực tiếp qua OmniRoute HTTP API (`http://127.0.0.1:20129/api/combos`) và backup vào `D:\Taadaa\AI-Tools\tools\omniroute\combos_backup.json`.
- Khi viết script verify ad-hoc:
  - Tra cứu trực tiếp endpoint `http://127.0.0.1:20129/api/combos` hoặc file `combos_backup.json` (chú ý đường dẫn không dùng escape `\t` tránh lỗi `\tools`).
  - Đối chiếu connectionId xuất hiện trong `models` của combo `ag-gemini-pool-3`.

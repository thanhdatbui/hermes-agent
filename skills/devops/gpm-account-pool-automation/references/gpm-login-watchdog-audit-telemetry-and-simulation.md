# GPM Login Watchdog Candidate Audit Telemetry & Test Simulation

## 1. Candidate Audit Telemetry Standard
Khi vận hành watchdog login tự động (như `post_evening_gpm_login_watchdog.py`), candidate filtering cần được log dạng structured audit telemetry để phục vụ audit/monitoring:

```python
def log_candidate_audit(action: str, email: str, reason: str, mid: int | None = None, port: str | None = None):
    log(f"[AUDIT] action={action} email={email} mid={mid} port={port} reason={reason}")
```

### Audit Actions & Rejection Reasons:
1. `ACCEPT`: Candidate thỏa mãn điều kiện và được lên lịch login (`cooldown_expired`, `has_google_session_ready_oauth`, `chatgpt_ready_priority`, `ready_gpm_oauth`).
2. `REJECT`:
   - `soak_missing_created_date` / `soak_clean_map_<days>d_lt_7d` / `soak_master_<days>d_lt_7d`: Thất bại tiêu chuẩn ngâm an toàn 7 ngày (fail-closed).
   - `already_processed`: Đã xử lý trong ngày.
   - `already_omniroute_success`: Đã active trên OmniRoute (:20129).
   - `excluded_status`: Thuộc danh sách loại trừ hoặc cooldown chưa hết hạn.
   - `not_in_gpm_db`: Profile chưa tồn tại trong GPMLogin DB.
   - `duplicate_mid_M<mid>`: Máy đã được lên lịch trong cùng batch (ràng buộc 1 máy/batch).
   - `proxy_limit_reached_<port>`: Port proxy đã đạt limit (tối đa 2 acc/port/ngày).
   - `machine_M<mid>_not_idle`: Máy đang bận ca nuôi hoặc lock device.
   - `offline_adb_serial_<serial>`: Thiết bị không online qua ADB.

## 2. Worker Error Isolation Pattern
Khi submit jobs qua `ThreadPoolExecutor`, map trực tiếp `future -> candidate` để bọc try-except tại `as_completed()`, đảm bảo một worker crash/exception không đánh sập vòng lặp `main()` và vẫn ghi nhận `status: FAIL`:

```python
fut_map = {}
for c in batch:
    fut = ex.submit(run_login, c)
    fut_map[fut] = c

for fut in as_completed(fut_map):
    c_item = fut_map[fut]
    try:
        res = fut.result()
    except Exception as ex_worker:
        log(f"[WORKER-ERR] {c_item.get('email')}: {ex_worker}")
        res = {**c_item, "status": "FAIL", "error": str(ex_worker)}
    ...
```

## 3. End-to-End Simulation Test Pattern (`TestEndToEndMainSimulation`)
Khi test watchdog `main()`:
1. Mock `is_within_time_window` = True.
2. Mock `is_avatar_done` = True.
3. Mock `get_candidates` trả về candidate giả lập.
4. Mock `get_online_adb_serials`, `get_machine_serial_map`, `is_machine_idle` = True.
5. Mock `time.sleep` để tránh bị delay thực thi trong tests.
6. Verify rollback/error isolation khi `run_login` raise Exception -> script không crash, state ghi nhận fail và `total_fail += 1`.

# Active Profile Tracking & Force Emergency Cleanup in Multi-Worker Batch GPM / Playwright

## 1. Vấn đề cốt lõi (Root Cause)
Trong các script chạy batch đa luồng (`ThreadPoolExecutor`) kết hợp GPM Local API và Playwright CDP:
- Khi gặp lỗi cấu trúc/hạ tầng liên tiếp (Circuit Breaker kích hoạt), nếu script chỉ set `SHUTDOWN_EVENT` và `break` khỏi vòng lặp `as_completed(futures)`:
  1. Các worker thread đang chạy dở có thể bị treo tại `page.goto()`, `connect_over_cdp()`, hoặc các thao tác mạng.
  2. Context manager `with ThreadPoolExecutor(...) as executor:` khi thoát sẽ tự động gọi `executor.shutdown(wait=True)`. Điều này khiến tiến trình chính bị BLOCK (treo vô hạn hoặc chờ hàng chục giây đến khi timeout), không thể thoát ngay.
  3. Các cửa sổ trình duyệt GPM / tiến trình `chrome.exe` của worker đang chạy không được giải phóng kịp thời, gây lãng phí tài nguyên và rủi ro cho tài khoản.

## 2. Kiến trúc giải pháp chuẩn

### A. Registry theo dõi Active Profiles & Thread Lock
```python
import os
import threading
import psutil
import requests

SHUTDOWN_EVENT = threading.Event()
ACTIVE_RUNNING_PROFILES = {}  # {p_id: (p_path, browser_ref, email)}
RUNNING_LOCK = threading.Lock()
```

### B. Hàm Cưỡng Chế Dọn Dẹp Khẩn Cấp (`force_emergency_cleanup`)
Duyệt qua tất cả profile đang hoạt động, chủ động đóng Playwright browser (làm cho các lệnh `page.*` trong worker ném exception lập tức) và kill sạch process Chrome qua GPM API + psutil:
```python
def force_emergency_cleanup():
    logger.critical("[EMERGENCY] Thực hiện cưỡng chế đóng toàn bộ profile đang chạy...")
    with RUNNING_LOCK:
        for pid, (ppath, browser, em) in list(ACTIVE_RUNNING_PROFILES.items()):
            try:
                if browser:
                    browser.close()
            except Exception:
                pass
            try:
                stop_and_kill_gpm_profile(pid, ppath)
            except Exception:
                pass
            logger.critical(f"[EMERGENCY] Đã dọn dẹp khẩn cấp profile: {em} ({pid})")
        ACTIVE_RUNNING_PROFILES.clear()
```

### C. Đăng ký & Giải phóng trong `process_single_profile`
```python
def process_single_profile(profile):
    p_id = profile["id"]
    email = profile["email"]
    
    # ... khởi động profile lấy addr và actual_path ...
    addr, actual_path, start_err = start_gpm_profile(p_id)
    if not addr:
        return {"success": False, "error": start_err}

    p_path_clean = actual_path or profile.get("profile_path", "")

    # Đăng ký ngay khi profile bắt đầu chạy
    with RUNNING_LOCK:
        ACTIVE_RUNNING_PROFILES[p_id] = (p_path_clean, None, email)

    try:
        if SHUTDOWN_EVENT.is_set():
            return {"success": False, "error": "Circuit Breaker Triggered"}

        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(f"http://{addr}", timeout=15000)
            
            # Cập nhật browser reference sau khi kết nối CDP thành công
            with RUNNING_LOCK:
                ACTIVE_RUNNING_PROFILES[p_id] = (p_path_clean, browser, email)

            # ... xử lý tự động hóa ...
            try:
                browser.close()
            except Exception:
                pass
    finally:
        # Giải phóng khỏi registry và kill tiến trình sạch sẽ
        with RUNNING_LOCK:
            ACTIVE_RUNNING_PROFILES.pop(p_id, None)
        stop_and_kill_gpm_profile(p_id, p_path_clean)
```

### D. Xử lý trong `main()` khi Circuit Breaker kích hoạt
```python
if consecutive_structural_fails >= MAX_CONSECUTIVE_STRUCTURAL_FAILS:
    logger.critical("!!! KÍCH HOẠT CIRCUIT BREAKER: Gặp lỗi cấu trúc liên tiếp !!!")
    SHUTDOWN_EVENT.set()
    force_emergency_cleanup()  # Kill ngay lập tức mọi browser/chrome đang chạy
    for f in futures:
        if not f.done():
            f.cancel()
    # Lưu báo cáo tiến độ hiện tại
    try:
        with open(REPORT_FILE, "w", encoding="utf-8") as f_rep:
            json.dump(results, f_rep, ensure_ascii=False, indent=2)
    except Exception:
        pass
    logger.critical("[CIRCUIT BREAKER] Thoát tiến trình ngay lập tức, không chờ kẹt executor!")
    os._exit(1)
```
